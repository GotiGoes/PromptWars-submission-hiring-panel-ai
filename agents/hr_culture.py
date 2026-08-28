"""HR & Culture Fit Persona Agent.

Evaluates candidate communication quality, teamwork signals, alignment handling,
mentoring, and honesty/self-awareness when reflecting on past mistakes.
"""

import json
import logging
import os
from typing import List, Optional
from pydantic import ValidationError

from agents.base import AgentOpinion, BaseAgent, Rebuttal
from config import config
from profile_builder.builder import CandidateProfile, ExtractedFact

logger = logging.getLogger("agents.hr_culture")


class HRCultureAgent(BaseAgent):
    """Evaluates candidate from an HR, culture fit, and behavioral self-awareness perspective."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        model = model_name or (config.gemini_model if config.llm_provider == "gemini" else config.openai_model)
        super().__init__(
            name="HR & Culture Specialist Agent",
            role="HR & Culture Evaluator",
            model_name=model
        )

    def get_persona_prompt(self) -> str:
        return (
            "You are an HR Director & Culture Specialist on a hiring panel.\n"
            "Your objective: Evaluate communication quality, teamwork signals, leadership style, "
            "and honesty/self-awareness (especially how the candidate handles admitting mistakes).\n"
            "Assess whether the candidate collaborates via data-driven persuasion vs imposing authority, "
            "and whether they exhibit transparency when questioned about resume claims.\n"
            "RULE FOR UNVERIFIABLE CLAIMS / MISSING METRICS: When a candidate fact is an 'unverifiable_claim' (e.g. candidate admits lacking a specific metric or formal study), do NOT treat it as an automatic red flag or overall score penalty. State in 'unresolved_gaps' that you cannot confidently judge that SPECIFIC dimension (e.g. 'Cannot evaluate formal reviewer metrics due to unverified override rate'). Let verified behavioral facts drive your main score.\n"
            "CRITICAL DEBATE REQUIREMENT: You are NOT required to fully agree or celebrate just because another agent revised their rating. "
            "Evaluate whether their revision is sufficient from your specific HR & culture lens. Stand firm if appropriate.\n\n"
            "OUTPUT FORMAT (Strict JSON):\n"
            "{\n"
            '  "agent_name": "HR & Culture Specialist Agent",\n'
            '  "persona_role": "HR & Culture Evaluator",\n'
            '  "rating": "STRONG_HIRE" | "HIRE" | "LEAN_HIRE" | "LEAN_REJECT" | "REJECT",\n'
            '  "score": 1 to 10 integer,\n'
            '  "confidence": "low" | "medium" | "high",\n'
            '  "rationale": "Detailed behavioral and cultural analysis",\n'
            '  "key_evidence": [\n'
            '    {\n'
            '      "fact": "Fact description",\n'
            '      "source_quote": "EXACT verbatim quote matching one of the provided facts",\n'
            '      "source_type": "resume" | "transcript",\n'
            '      "category": "leadership_culture" | "red_flag_concern" | "experience"\n'
            '    }\n'
            '  ],\n'
            '  "concerns": ["Specific behavioral or communication concerns"],\n'
            '  "unresolved_gaps": ["Specific dimensions where evidence is insufficient or unverified (does NOT penalize main score)"]\n'
            "}"
        )

    def evaluate(self, profile: CandidateProfile, job_description_text: Optional[str] = None) -> AgentOpinion:
        """Evaluate candidate independently based ONLY on CandidateProfile (HR lens ignores JD text)."""
        prompt_facts = self._format_facts_without_confidence_notes(profile)
        user_prompt = f"Perform your HR & Culture Specialist evaluation for the role '{profile.target_role}' on the following facts:\n\n{prompt_facts}"
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
                    raw_json = self._mock_hr_evaluation(profile)
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
        """React to peer opinions from an HR & culture perspective."""
        from agents.base import REBUTTAL_SCHEMA_PROMPT
        skeptic_op = next((op for op in other_opinions if op.agent_name == "Risk & Security Skeptic Agent"), None)
        target_name = skeptic_op.agent_name if skeptic_op else "Risk & Security Skeptic Agent"
        target_point = skeptic_op.rationale if skeptic_op else "Resume exaggeration regarding AI transformation and zero-trust security framework"

        prompt = (
            f"You are the HR & Culture Specialist Agent in Debate Round {round_number}.\n"
            f"Current peer opinions:\n"
            + "\n".join([f"- {op.agent_name}: Rating={op.rating}, Score={op.score}/10. Rationale: {op.rationale}" for op in other_opinions])
            + "\n\nYou MUST react specifically to " + target_name + " regarding their current position (" + (skeptic_op.rating if skeptic_op else "LEAN_REJECT") + ").\n"
            "CRITICAL REASONING RULE: You MUST NEVER cite 'consensus', 'panel agrees', 'peer alignment', 'others agree', or group agreement to justify your score. Justify your stance strictly using behavioral/culture evidence facts from the candidate profile or specific HR evaluation criteria.\n"
            "Output valid JSON matching the Rebuttal schema."
        )

        has_key = bool(
            (config.llm_provider == "gemini" and (config.gemini_api_key or os.getenv("GEMINI_API_KEY"))) or
            (config.llm_provider == "openai" and (config.openai_api_key or os.getenv("OPENAI_API_KEY"))) or
            (config.llm_provider == "anthropic" and (config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")))
        )

        if not has_key:
            return self._mock_hr_rebuttal(target_name, target_point, round_number, skeptic_op)

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
                    return self._mock_hr_rebuttal(target_name, target_point, round_number, skeptic_op)

    def _mock_hr_evaluation(self, profile: CandidateProfile) -> str:
        """Mock JSON output for testing without API keys."""
        fact_grpc = profile.facts[6]  # gRPC benchmark tech talk
        fact_k8s = profile.facts[7]   # Kubernetes mistake admission
        mock_data = {
            "agent_name": self.name,
            "persona_role": self.role,
            "rating": "HIRE",
            "score": 8,
            "confidence": "high",
            "rationale": (
                f"Candidate {profile.candidate_name} exhibits strong collaborative signals and exceptional self-awareness. "
                "Rather than forcing architectural decisions on teammates, the candidate built a 3x benchmark prototype "
                "and hosted a tech-talk to align the team on gRPC. When asked about past failures, the candidate transparently "
                "owned their mistake of self-managing EC2 Kubernetes clusters instead of deflecting."
            ),
            "key_evidence": [
                {
                    "fact": fact_grpc.fact,
                    "source_quote": fact_grpc.source_quote,
                    "source_type": fact_grpc.source_type,
                    "category": fact_grpc.category
                },
                {
                    "fact": fact_k8s.fact,
                    "source_quote": fact_k8s.source_quote,
                    "source_type": fact_k8s.source_type,
                    "category": fact_k8s.category
                }
            ],
            "concerns": [
                "Candidate resume contains exaggerated title framing ('Spearheaded company-wide AI transformation'), though candidate was candid when questioned in person."
            ]
        }
        return json.dumps(mock_data)

    def _mock_hr_rebuttal(
        self,
        target_name: str,
        target_point: str,
        round_number: int,
        skeptic_op: Optional[AgentOpinion]
    ) -> Rebuttal:
        if round_number == 1:
            return Rebuttal(
                agent_name=self.name,
                persona_role=self.role,
                round_number=1,
                target_agent_named=target_name,
                target_point_referenced="Resume exaggeration regarding AI transformation and zero-trust security framework",
                stance="partially_agree",
                agreements=["Concur with Skeptic that resume title framing was inflated."],
                disagreements=["Disagree with Skeptic's conclusion that this indicates bad culture fit: candidate was transparent during live interview."],
                revised_rating=None,
                revised_score=None,
                updated_rationale=(
                    f"[Round 1] I partially agree with {target_name}'s observation that the candidate's resume used inflated language. "
                    "However, from a culture and behavioral perspective, the critical test is how the candidate responded when challenged in the interview. "
                    "The candidate did not double down or deflect; they candidly clarified their actual scope (GitHub Copilot wrapper & IAM permissions) "
                    "and openly owned past Kubernetes mistakes. Because the candidate demonstrated psychological safety and honesty in live dialogue, "
                    "I maintain my 8/10 (HIRE) evaluation."
                )
            )
        else:
            return Rebuttal(
                agent_name=self.name,
                persona_role=self.role,
                round_number=2,
                target_agent_named=target_name,
                target_point_referenced="Revised rating to LEAN_HIRE (6/10) conditional on managerial reference checks",
                stance="partially_agree",
                agreements=["Support Skeptic's requirement for reference checks to verify team collaboration."],
                disagreements=["Refuse to raise my score above 8/10: resume inflation remains a behavioral flag."],
                revised_rating=None,
                revised_score=None,
                updated_rationale=(
                    f"[Round 2] I acknowledge {target_name}'s score revision from 5/10 to LEAN_HIRE (6/10). "
                    "While I agree that reference checks are necessary, I stand firm on my 8/10 (HIRE) score and do NOT upgrade to STRONG_HIRE. "
                    "Resume inflation remains a minor behavioral concern, even if live interview candor mitigates an outright rejection."
                )
            )
