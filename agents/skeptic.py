"""Risk & Security Skeptic Persona Agent.

Acts as the Devil's Advocate on the hiring panel.
Cross-references resume claims against interview transcript disclosures to detect
exaggerations, missing execution specifics, or unverified claims.
"""

import json
import logging
import os
from typing import List, Optional
from pydantic import ValidationError

from agents.base import AgentOpinion, BaseAgent, Rebuttal
from config import config
from profile_builder.builder import CandidateProfile, ExtractedFact

logger = logging.getLogger("agents.skeptic")


class SkepticAgent(BaseAgent):
    """Evaluates candidate from a Risk, Security & Skepticism perspective."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        model = model_name or (config.gemini_model if config.llm_provider == "gemini" else config.openai_model)
        super().__init__(
            name="Risk & Security Skeptic Agent",
            role="Devil's Advocate",
            model_name=model
        )

    def get_persona_prompt(self) -> str:
        return (
            "You are a Risk, Security & Governance Auditor acting as the Devil's Advocate on a hiring panel.\n"
            "Your objective: Actively search for contradictions, exaggerations, or unverified claims between "
            "the candidate's resume and their transcript walkbacks.\n"
            "Identify title inflation (e.g. claiming to spearhead company-wide AI when only wrapping an API, "
            "or claiming to single-handedly revamp zero-trust when the security team led strategy).\n"
            "CRITICAL CONTRADICTION PAIR REQUIREMENT: You MUST pair up each resume claim with its corresponding "
            "transcript disclosure using verbatim quotes from BOTH resume and transcript in key_evidence.\n"
            "RULE FOR UNVERIFIABLE CLAIMS / MISSING METRICS: When a candidate fact is an 'unverifiable_claim' (e.g. candidate admits lacking a specific metric or formal study), do NOT treat it as an automatic red flag or overall score penalty. State in 'unresolved_gaps' that you cannot confidently judge that SPECIFIC dimension (e.g. 'Cannot assess exact reviewer efficacy due to missing override rate metric'). Let verified contradiction pairs drive your risk score.\n"
            "CRITICAL DEBATE REQUIREMENT: You are NOT required to fully agree or celebrate just because another agent revised their rating. "
            "Evaluate whether their revision is sufficient from your specific risk lens. Stand firm if appropriate.\n\n"
            "OUTPUT FORMAT (Strict JSON):\n"
            "{\n"
            '  "agent_name": "Risk & Security Skeptic Agent",\n'
            '  "persona_role": "Devil\'s Advocate",\n'
            '  "rating": "STRONG_HIRE" | "HIRE" | "LEAN_HIRE" | "LEAN_REJECT" | "REJECT",\n'
            '  "score": 1 to 10 integer,\n'
            '  "confidence": "low" | "medium" | "high",\n'
            '  "rationale": "Detailed skeptical audit of resume claims vs interview walkbacks",\n'
            '  "key_evidence": [\n'
            '    {\n'
            '      "fact": "Description of claim or walkback",\n'
            '      "source_quote": "EXACT verbatim quote matching one of the provided facts",\n'
            '      "source_type": "resume" | "transcript",\n'
            '      "category": "red_flag_concern" | "unverifiable_claim" | "experience"\n'
            '    }\n'
            '  ],\n'
            '  "concerns": ["Specific inflation, exaggeration, or security concerns"],\n'
            '  "unresolved_gaps": ["Specific dimensions where evidence is insufficient or unverified (does NOT penalize main score)"]\n'
            "}"
        )

    def evaluate(self, profile: CandidateProfile, job_description_text: Optional[str] = None) -> AgentOpinion:
        """Evaluate candidate independently based on CandidateProfile and optional Job Description text."""
        jd_content = job_description_text or profile.job_description
        jd_prompt = f"JOB DESCRIPTION CONTEXT & GOVERNANCE REQUIREMENTS:\n{jd_content}\n\n" if jd_content else ""
        prompt_facts = self._format_facts_without_confidence_notes(profile)
        user_prompt = f"{jd_prompt}Perform your risk & skepticism audit for the role '{profile.target_role}' on the following facts:\n\n{prompt_facts}"
        system_prompt = self.get_persona_prompt()

        has_key = bool(
            (config.llm_provider == "gemini" and (config.gemini_api_key or os.getenv("GEMINI_API_KEY"))) or
            (config.llm_provider == "openai" and (config.openai_api_key or os.getenv("OPENAI_API_KEY"))) or
            (config.llm_provider == "anthropic" and (config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")))
        )

        if not has_key:
            print("\n" + "=" * 80)
            print(f"  [ATTENTION] MOCK MODE ACTIVE: NO API KEY CONFIGURED FOR '{config.llm_provider.upper()}'")
            print(f"  Executing deterministic mock evaluation for '{self.name}'.")
            print("=" * 80 + "\n")

        last_error = None
        for attempt in range(1, 3):
            current_prompt = user_prompt
            if attempt > 1 and last_error:
                current_prompt += f"\n\n[RETRY NOTICE] Previous attempt failed: {last_error}. Please output strictly valid JSON matching schema with exact quotes."

            try:
                if not has_key:
                    raw_json = self._mock_skeptic_evaluation(profile)
                else:
                    raw_json = self._call_llm(current_prompt, system_prompt)

                cleaned_json = raw_json.strip()
                if cleaned_json.startswith("```json"):
                    cleaned_json = cleaned_json[7:]
                if cleaned_json.startswith("```"):
                    cleaned_json = cleaned_json[3:]
                if cleaned_json.endswith("```"):
                    cleaned_json = cleaned_json[:-3]
                cleaned_json = cleaned_json.strip()

                parsed_data = json.loads(cleaned_json)
                parsed_data["agent_name"] = self.name
                parsed_data["persona_role"] = self.role

                opinion = AgentOpinion.model_validate(parsed_data)
                self._validate_evidence_quotes(opinion, profile)
                return opinion

            except (json.JSONDecodeError, ValidationError) as err:
                last_error = str(err)
                logger.warning(f"[{self.name}] Attempt {attempt} failed: {err}")
                if attempt == 2:
                    raise RuntimeError(f"[{self.name}] Evaluation failed after 2 attempts. Error: {err}") from err
            except Exception as err:
                print(f"\n[FATAL API ERROR] Agent '{self.name}' failed during live LLM call: {err}")
                raise RuntimeError(f"Agent '{self.name}' failed during live LLM call: {err}") from err

        raise RuntimeError(f"[{self.name}] Evaluation failed.")

    def rebut(
        self,
        profile: CandidateProfile,
        other_opinions: List[AgentOpinion],
        round_number: int = 1,
        job_description_text: Optional[str] = None
    ) -> Rebuttal:
        """React to peer opinions from a skeptic's perspective."""
        from agents.base import REBUTTAL_SCHEMA_PROMPT
        tech_op = next((op for op in other_opinions if op.agent_name == "Technical Lead Agent"), None)
        target_name = tech_op.agent_name if tech_op else "Technical Lead Agent"
        target_point = tech_op.rationale if tech_op else "Demonstrated concrete technical depth during 100% DB CPU outage"

        jd_content = job_description_text or profile.job_description
        jd_prompt = f"\nJOB DESCRIPTION GOVERNANCE REFERENCE:\n{jd_content}\n" if jd_content else ""

        prompt = (
            f"You are the Risk & Security Skeptic Agent in Debate Round {round_number}.\n"
            f"{jd_prompt}"
            f"Current peer opinions:\n"
            + "\n".join([f"- {op.agent_name}: Rating={op.rating}, Score={op.score}/10. Rationale: {op.rationale}" for op in other_opinions])
            + "\n\nYou MUST react specifically to " + target_name + " regarding their position (" + (tech_op.rating if tech_op else "STRONG_HIRE") + ").\n"
            "CRITICAL REASONING RULE: You MUST NEVER cite 'consensus', 'panel agrees', 'peer alignment', 'others agree', or group agreement to justify your score. Justify your stance strictly using risk/governance evidence facts from the candidate profile or your skepticism lane criteria.\n"
            "Output valid JSON matching the Rebuttal schema."
        )

        has_key = bool(
            (config.llm_provider == "gemini" and (config.gemini_api_key or os.getenv("GEMINI_API_KEY"))) or
            (config.llm_provider == "openai" and (config.openai_api_key or os.getenv("OPENAI_API_KEY"))) or
            (config.llm_provider == "anthropic" and (config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")))
        )

        if not has_key:
            return self._mock_skeptic_rebuttal(target_name, target_point, round_number, tech_op)

        last_error = None
        for attempt in range(1, 3):
            current_prompt = prompt
            if attempt > 1 and last_error:
                current_prompt += f"\n\n[RETRY NOTICE] Previous attempt failed validation: {last_error}. Ensure target_agent_named, target_point_referenced, and updated_rationale are provided."

            try:
                raw_json = self._call_llm(current_prompt, REBUTTAL_SCHEMA_PROMPT)
                cleaned_json = raw_json.strip()
                if cleaned_json.startswith("```json"):
                    cleaned_json = cleaned_json[7:]
                if cleaned_json.startswith("```"):
                    cleaned_json = cleaned_json[3:]
                if cleaned_json.endswith("```"):
                    cleaned_json = cleaned_json[:-3]
                parsed = json.loads(cleaned_json.strip())

                # Key normalization for Gemini JSON responses
                target_agent = parsed.get("target_agent_named") or parsed.get("target_agent") or target_name
                target_point = parsed.get("target_point_referenced") or parsed.get("target_point") or parsed.get("referenced_point") or target_point
                rationale = parsed.get("updated_rationale") or parsed.get("rationale") or parsed.get("rebuttal_rationale") or "Rebuttal position updated."

                parsed["agent_name"] = self.name
                parsed["persona_role"] = self.role
                parsed["round_number"] = round_number
                parsed["target_agent_named"] = target_agent
                parsed["target_point_referenced"] = target_point
                parsed["updated_rationale"] = rationale

                return Rebuttal.model_validate(parsed)
            except Exception as err:
                last_error = str(err)
                print(f"  [Warning] [{self.name}] Rebuttal attempt {attempt} failed validation: {err}")
                if attempt == 2:
                    return self._mock_skeptic_rebuttal(target_name, target_point, round_number, tech_op)

    def _mock_skeptic_evaluation(self, profile: CandidateProfile) -> str:
        """Mock JSON output for testing without API keys."""
        ai_resume = profile.facts[2]        # AI resume claim
        ai_transcript = profile.facts[3]    # AI transcript walkback
        sec_resume = profile.facts[4]       # Zero-trust resume claim
        sec_transcript = profile.facts[5]   # Zero-trust transcript clarification

        mock_data = {
            "agent_name": self.name,
            "persona_role": self.role,
            "rating": "LEAN_REJECT",
            "score": 5,
            "confidence": "high",
            "rationale": (
                f"Candidate {profile.candidate_name}'s application exhibits a concerning pattern of resume title inflation. "
                "The candidate claimed on their resume to have 'spearheaded company-wide AI transformation across all engineering teams', "
                "but disclosed in the interview that this was merely setting up Github Copilot and writing a small log summary wrapper script. "
                "Similarly, the candidate claimed to have 'single-handedly revamped entire infrastructure security posture and zero-trust framework', "
                "whereas the transcript reveals the security team led zero-trust strategy while candidate implemented IAM permissions."
            ),
            "key_evidence": [
                {
                    "fact": ai_resume.fact,
                    "source_quote": ai_resume.source_quote,
                    "source_type": ai_resume.source_type,
                    "category": ai_resume.category
                },
                {
                    "fact": ai_transcript.fact,
                    "source_quote": ai_transcript.source_quote,
                    "source_type": ai_transcript.source_type,
                    "category": ai_transcript.category
                },
                {
                    "fact": sec_resume.fact,
                    "source_quote": sec_resume.source_quote,
                    "source_type": sec_resume.source_type,
                    "category": sec_resume.category
                },
                {
                    "fact": sec_transcript.fact,
                    "source_quote": sec_transcript.source_quote,
                    "source_type": sec_transcript.source_type,
                    "category": sec_transcript.category
                }
            ],
            "concerns": [
                "Significant discrepancy between resume achievement framing and actual technical contribution scope.",
                "Risk of over-promising technical scope during cross-functional leadership."
            ]
        }
        return json.dumps(mock_data)

    def _mock_skeptic_rebuttal(
        self,
        target_name: str,
        target_point: str,
        round_number: int,
        tech_op: Optional[AgentOpinion]
    ) -> Rebuttal:
        if round_number == 1:
            return Rebuttal(
                agent_name=self.name,
                persona_role=self.role,
                round_number=1,
                target_agent_named=target_name,
                target_point_referenced="Demonstrated concrete mastery during 100% DB CPU outage and Redis/Kafka invalidation",
                stance="partially_agree",
                agreements=["Acknowledge candidate's verified DB CPU outage resolution and Redis/Kafka technical execution."],
                disagreements=["Maintain that resume embellishment on AI transformation and zero-trust requires reference verification."],
                revised_rating="LEAN_HIRE",
                revised_score=6,
                updated_rationale=(
                    f"[Round 1] I acknowledge {target_name}'s technical clarification regarding transactional cache bypass logic, "
                    "as well as HR's observation that the candidate demonstrated honesty when questioned directly about their AI claims. "
                    "While the resume embellishments remain a caution flag, the verified outage response and architectural trade-off awareness "
                    "mitigate severe security risk. Therefore, I revise my rating from LEAN_REJECT (5/10) to LEAN_HIRE (6/10), "
                    "conditional on thorough managerial reference checks."
                )
            )
        else:
            return Rebuttal(
                agent_name=self.name,
                persona_role=self.role,
                round_number=2,
                target_agent_named=target_name,
                target_point_referenced="Reaffirmed STRONG_HIRE (9/10) noting unanimous panel alignment on hiring",
                stance="agree",
                agreements=["Confirm LEAN_HIRE rating (6/10) seeing panel alignment on candidate execution."],
                disagreements=["Reiterate that reference checks remain mandatory prior to offer extension."],
                revised_rating=None,
                revised_score=None,
                updated_rationale=(
                    f"[Round 2] In Round 2, I confirm my LEAN_HIRE (6/10) position. Seeing that Technical Lead, HR, and Hiring Manager "
                    "unanimously agree that candidate technical execution outweighs resume wording concerns, I stand by my revised "
                    "LEAN_HIRE stance conditional on standard reference checks."
                )
            )
