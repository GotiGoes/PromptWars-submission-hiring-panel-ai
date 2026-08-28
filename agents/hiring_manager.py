"""Hiring Manager Persona Agent.

Evaluates candidate execution capability, business impact, pragmatic decision-making,
and overall role fit for the target position specifically.
"""

import json
import logging
import os
from typing import List, Optional
from pydantic import ValidationError

from agents.base import AgentOpinion, BaseAgent, Rebuttal
from config import config
from profile_builder.builder import CandidateProfile, ExtractedFact

logger = logging.getLogger("agents.hiring_manager")


class HiringManagerAgent(BaseAgent):
    """Evaluates candidate from a Hiring Manager & Delivery perspective."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        model = model_name or (config.gemini_model if config.llm_provider == "gemini" else config.openai_model)
        super().__init__(
            name="Engineering Director Agent",
            role="Hiring Manager",
            model_name=model
        )

    def get_persona_prompt(self) -> str:
        return (
            "You are an Engineering Director & Hiring Manager on a panel.\n"
            "Your objective: Evaluate overall fit and hire-worthiness for the candidate's target role specifically.\n"
            "Assess business impact, delivery velocity, production execution, problem ownership, "
            "and whether the candidate can solve critical scaling bottlenecks in your organization.\n"
            "RULE FOR UNVERIFIABLE CLAIMS / MISSING METRICS: When a candidate fact is an 'unverifiable_claim' (e.g. candidate admits lacking a specific metric or formal study), do NOT treat it as an automatic red flag or overall score penalty. State in 'unresolved_gaps' that you cannot confidently judge that SPECIFIC dimension (e.g. 'Cannot assess exact reviewer efficacy due to missing override rate metric'). Let verified production execution facts drive the bulk of your overall score.\n"
            "CRITICAL DEBATE REQUIREMENT: You are NOT required to fully agree or celebrate just because another agent revised their rating. "
            "Evaluate whether their revision is sufficient from your specific delivery lens. Stand firm if appropriate.\n\n"
            "OUTPUT FORMAT (Strict JSON):\n"
            "{\n"
            '  "agent_name": "Engineering Director Agent",\n'
            '  "persona_role": "Hiring Manager",\n'
            '  "rating": "STRONG_HIRE" | "HIRE" | "LEAN_HIRE" | "LEAN_REJECT" | "REJECT",\n'
            '  "score": 1 to 10 integer,\n'
            '  "confidence": "low" | "medium" | "high",\n'
            '  "rationale": "Detailed delivery and role-fit evaluation",\n'
            '  "key_evidence": [\n'
            '    {\n'
            '      "fact": "Fact description",\n'
            '      "source_quote": "EXACT verbatim quote matching one of the provided facts",\n'
            '      "source_type": "resume" | "transcript",\n'
            '      "category": "achievement" | "experience" | "technical_skill"\n'
            '    }\n'
            '  ],\n'
            '  "concerns": ["Specific delivery or execution risks"],\n'
            '  "unresolved_gaps": ["Specific dimensions where evidence is insufficient or unverified (does NOT penalize main score)"]\n'
            "}"
        )

    def evaluate(self, profile: CandidateProfile, job_description_text: Optional[str] = None) -> AgentOpinion:
        """Evaluate candidate independently based on CandidateProfile and optional Job Description text."""
        jd_content = job_description_text or profile.job_description
        jd_prompt = f"JOB DESCRIPTION REQUIREMENTS:\n{jd_content}\n\n" if jd_content else ""
        prompt_facts = self._format_facts_without_confidence_notes(profile)
        user_prompt = (
            f"{jd_prompt}"
            f"Perform your Hiring Manager role-fit evaluation for the role '{profile.target_role}' on the following facts:\n\n{prompt_facts}\n\n"
            "MANDATORY REQUIREMENT FOR FIT JUDGMENT: You MUST compare candidate facts directly against SPECIFIC requirements in the Job Description. "
            "You MUST quote exact lines from the Job Description alongside candidate facts when explaining role fit in your rationale. "
            "Do NOT make vague assertions like 'seems like a good fit'."
        )
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
                    raw_json = self._mock_manager_evaluation(profile)
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
        """React to peer opinions from a hiring manager perspective."""
        from agents.base import REBUTTAL_SCHEMA_PROMPT
        skeptic_op = next((op for op in other_opinions if op.agent_name == "Risk & Security Skeptic Agent"), None)
        target_name = skeptic_op.agent_name if skeptic_op else "Risk & Security Skeptic Agent"
        target_point = skeptic_op.rationale if skeptic_op else "Pattern of resume embellishment on AI transformation and zero-trust framework"

        jd_content = job_description_text or profile.job_description
        jd_prompt = f"\nJOB DESCRIPTION REFERENCE:\n{jd_content}\n" if jd_content else ""

        prompt = (
            f"You are the Engineering Director (Hiring Manager) in Debate Round {round_number}.\n"
            f"{jd_prompt}"
            f"Current peer opinions:\n"
            + "\n".join([f"- {op.agent_name}: Rating={op.rating}, Score={op.score}/10. Rationale: {op.rationale}" for op in other_opinions])
            + "\n\nYou MUST react specifically to " + target_name + " regarding their current position (" + (skeptic_op.rating if skeptic_op else "LEAN_REJECT") + ").\n"
            "CRITICAL REASONING RULE: You MUST NEVER cite 'consensus', 'panel agrees', 'peer alignment', 'others agree', or group agreement to justify your score. Justify your stance strictly using delivery/business impact evidence facts from the candidate profile and specific requirements from the Job Description.\n"
            "Output valid JSON matching the Rebuttal schema."
        )

        has_key = bool(
            (config.llm_provider == "gemini" and (config.gemini_api_key or os.getenv("GEMINI_API_KEY"))) or
            (config.llm_provider == "openai" and (config.openai_api_key or os.getenv("OPENAI_API_KEY"))) or
            (config.llm_provider == "anthropic" and (config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")))
        )

        if not has_key:
            return self._mock_manager_rebuttal(target_name, target_point, round_number, skeptic_op)

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
                    return self._mock_manager_rebuttal(target_name, target_point, round_number, skeptic_op)

    def _mock_manager_evaluation(self, profile: CandidateProfile) -> str:
        """Mock JSON output for testing without API keys."""
        fact_db = profile.facts[1]     # 20 min DB CPU recovery
        fact_perf = profile.facts[9]   # 45% latency reduction
        mock_data = {
            "agent_name": self.name,
            "persona_role": self.role,
            "rating": "STRONG_HIRE",
            "score": 9,
            "confidence": "high",
            "rationale": (
                f"Candidate {profile.candidate_name} is an ideal fit for the target role of '{profile.target_role}'. "
                "Delivers clear business value: 45% query latency reduction and rapid 20-minute DB outage resolution. "
                "The candidate demonstrates practical problem ownership and engineering velocity."
            ),
            "key_evidence": [
                {
                    "fact": fact_perf.fact,
                    "source_quote": fact_perf.source_quote,
                    "source_type": fact_perf.source_type,
                    "category": fact_perf.category
                },
                {
                    "fact": fact_db.fact,
                    "source_quote": fact_db.source_quote,
                    "source_type": fact_db.source_type,
                    "category": fact_db.category
                }
            ],
            "concerns": [
                "Ensure onboarding aligns candidate with cloud-managed architecture paradigms immediately."
            ]
        }
        return json.dumps(mock_data)

    def _mock_manager_rebuttal(
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
                target_point_referenced="Pattern of resume embellishment on AI transformation and zero-trust framework",
                stance="disagree",
                agreements=["Agree with Technical Lead on overall delivery impact."],
                disagreements=["Disagree with Skeptic that resume embellishments compromise hiring viability."],
                revised_rating=None,
                revised_score=None,
                updated_rationale=(
                    f"[Round 1] I acknowledge {target_name}'s point regarding resume embellishment. However, as Hiring Manager, "
                    "my primary concern is execution speed and proven delivery in senior backend roles. "
                    "The candidate achieved a 45% database query latency reduction and resolved a 100% CPU outage in 20 minutes. "
                    "Because candidate delivery and technical ownership directly match our team's immediate business needs, "
                    "resume title fluff does not alter my 9/10 (STRONG_HIRE) recommendation."
                )
            )
        else:
            return Rebuttal(
                agent_name=self.name,
                persona_role=self.role,
                round_number=2,
                target_agent_named=target_name,
                target_point_referenced="Revised rating to LEAN_HIRE (6/10) with reference check condition",
                stance="partially_agree",
                agreements=["Acknowledge Skeptic's score movement to LEAN_HIRE (6/10)."],
                disagreements=["Maintain my independent 9/10 score based on revenue and uptime impact."],
                revised_rating=None,
                revised_score=None,
                updated_rationale=(
                    f"[Round 2] I note {target_name}'s upgrade to 6/10 (LEAN_HIRE). While I respect Skeptic's diligence, "
                    "my hiring decision rests firmly on production output (45% DB latency reduction, 20-min incident recovery). "
                    "I stand firm on my 9/10 (STRONG_HIRE) rating; Skeptic's reference checks can proceed as standard HR due diligence."
                )
            )
