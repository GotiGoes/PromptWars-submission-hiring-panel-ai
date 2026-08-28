"""Technical Evaluator Persona Agent.

Evaluates candidate technical depth, system architecture choices, query optimization,
and engineering trade-offs (e.g., Redis caching vs Postgres ACID compliance).
"""

import json
import logging
import os
from typing import List, Optional
from pydantic import ValidationError

from agents.base import AgentOpinion, BaseAgent, Rebuttal
from config import config
from profile_builder.builder import CandidateProfile, ExtractedFact

logger = logging.getLogger("agents.technical")


class TechnicalAgent(BaseAgent):
    """Evaluates candidate from a technical lead / system architect perspective."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        model = model_name or (config.gemini_model if config.llm_provider == "gemini" else config.openai_model)
        super().__init__(
            name="Technical Lead Agent",
            role="Technical Evaluator",
            model_name=model
        )

    def get_persona_prompt(self) -> str:
        return (
            "You are a Principal Software Engineer & Architect on a hiring panel.\n"
            "Your objective: Evaluate the depth and credibility of technical claims vs. what is "
            "actually demonstrated with concrete specifics in the transcript.\n"
            "Analyze system design choices, API throughput, data retrieval pipelines, and architectural trade-offs "
            "based strictly on the facts provided in the candidate profile.\n"
            "RULE FOR UNVERIFIABLE CLAIMS / MISSING METRICS: When a candidate fact is an 'unverifiable_claim' (e.g. candidate admits lacking a specific metric like override rate or formal study), do NOT treat it as an automatic red flag or overall score penalty. Instead, state in 'unresolved_gaps' that you cannot confidently judge that SPECIFIC dimension (e.g. 'Cannot assess exact reviewer agent efficacy due to missing override rate metric'). Let verified technical facts drive the bulk of your overall score.\n"
            "CRITICAL DEBATE REQUIREMENT: You are NOT required to fully agree or celebrate just because another agent revised their rating. "
            "Evaluate whether their revision is sufficient from your specific technical lens. Stand firm if appropriate.\n\n"
            "OUTPUT FORMAT (Strict JSON):\n"
            "{\n"
            '  "agent_name": "Technical Lead Agent",\n'
            '  "persona_role": "Technical Evaluator",\n'
            '  "rating": "STRONG_HIRE" | "HIRE" | "LEAN_HIRE" | "LEAN_REJECT" | "REJECT",\n'
            '  "score": 1 to 10 integer,\n'
            '  "confidence": "low" | "medium" | "high",\n'
            '  "rationale": "Detailed technical analysis of demonstrated architecture capabilities",\n'
            '  "key_evidence": [\n'
            '    {\n'
            '      "fact": "Fact description",\n'
            '      "source_quote": "EXACT verbatim quote matching one of the provided facts",\n'
            '      "source_type": "resume" | "transcript",\n'
            '      "category": "technical_skill" | "experience" | "achievement"\n'
            '    }\n'
            '  ],\n'
            '  "concerns": ["Specific technical concerns or risks"],\n'
            '  "unresolved_gaps": ["Specific dimensions where evidence is insufficient or unverified (does NOT penalize main score)"]\n'
            "}"
        )

    def evaluate(self, profile: CandidateProfile, job_description_text: Optional[str] = None) -> AgentOpinion:
        """Evaluate candidate independently based ONLY on CandidateProfile (technical lens ignores JD text)."""
        prompt_facts = self._format_facts_without_confidence_notes(profile)
        user_prompt = f"Perform your Technical Lead evaluation for the role '{profile.target_role}' on the following facts:\n\n{prompt_facts}"
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
                    raw_json = self._mock_technical_evaluation(profile)
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
        """React to peer opinions during the cross-agent debate round."""
        from agents.base import REBUTTAL_SCHEMA_PROMPT
        skeptic_op = next((op for op in other_opinions if op.agent_name == "Risk & Security Skeptic Agent"), None)
        target_name = skeptic_op.agent_name if skeptic_op else "Risk & Security Skeptic Agent"
        target_point = skeptic_op.rationale if skeptic_op else "Pattern of resume embellishment on AI transformation and zero-trust framework"

        prompt = (
            f"You are the Technical Lead Agent in Debate Round {round_number}.\n"
            f"Here are the current peer opinions:\n"
            + "\n".join([f"- {op.agent_name} ({op.persona_role}): Rating={op.rating}, Score={op.score}/10. Rationale: {op.rationale}" for op in other_opinions])
            + "\n\nYou MUST react specifically to " + target_name + " regarding their current stance (" + (skeptic_op.rating if skeptic_op else "LEAN_REJECT") + ").\n"
            "CRITICAL REASONING RULE: You MUST NEVER cite 'consensus', 'panel agrees', 'peer alignment', 'others agree', or group agreement to justify your score. Justify your stance strictly using technical evidence facts from the candidate profile or specific technical architecture criteria.\n"
            "Output valid JSON matching the Rebuttal schema."
        )

        has_key = bool(
            (config.llm_provider == "gemini" and (config.gemini_api_key or os.getenv("GEMINI_API_KEY"))) or
            (config.llm_provider == "openai" and (config.openai_api_key or os.getenv("OPENAI_API_KEY"))) or
            (config.llm_provider == "anthropic" and (config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")))
        )

        if not has_key:
            return self._mock_technical_rebuttal(target_name, target_point, round_number, skeptic_op)

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
                    return self._mock_technical_rebuttal(target_name, target_point, round_number, skeptic_op)

    def _mock_technical_evaluation(self, profile: CandidateProfile) -> str:
        """Mock JSON output for testing without API keys."""
        fact_1 = profile.facts[0]  # 50k RPS
        fact_2 = profile.facts[1]  # 20 min DB CPU recovery
        mock_data = {
            "agent_name": self.name,
            "persona_role": self.role,
            "rating": "STRONG_HIRE",
            "score": 9,
            "confidence": "high",
            "rationale": (
                f"Candidate {profile.candidate_name} exhibits top-tier technical depth in distributed systems. "
                "Demonstrated concrete mastery during a 100% DB CPU outage by isolating slow query JOINs, introducing "
                "a Redis read-cache with Kafka invalidation, and adding composite indexes to restore system health in 20 minutes. "
                "Furthermore, financial transaction bypass logic shows sound architectural trade-off awareness."
            ),
            "key_evidence": [
                {
                    "fact": fact_1.fact,
                    "source_quote": fact_1.source_quote,
                    "source_type": fact_1.source_type,
                    "category": fact_1.category
                },
                {
                    "fact": fact_2.fact,
                    "source_quote": fact_2.source_quote,
                    "source_type": fact_2.source_type,
                    "category": fact_2.category
                }
            ],
            "concerns": [
                "Self-managed EC2 Kubernetes cluster attempt shows initial over-engineering tendency prior to adopting managed EKS."
            ]
        }
        return json.dumps(mock_data)

    def _mock_technical_rebuttal(
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
                stance="partially_agree",
                agreements=["Acknowledge Skeptic's point that resume title framing for AI transformation was inflated."],
                disagreements=["Push back on Skeptic's LEAN_REJECT rating: resume buzzword framing does not diminish verified production execution."],
                revised_rating=None,
                revised_score=None,
                updated_rationale=(
                    f"[Round 1] I acknowledge {target_name}'s point regarding resume exaggeration on AI transformation. "
                    "However, as Technical Lead, my lane focuses strictly on verified system design and production execution "
                    "(50,000+ RPS microservices, 20-minute DB outage recovery, Kafka invalidation with transactional bypass). "
                    "Because resume marketing wording does not invalidate proven technical competency, I maintain my 9/10 (STRONG_HIRE) rating."
                )
            )
        else:
            return Rebuttal(
                agent_name=self.name,
                persona_role=self.role,
                round_number=2,
                target_agent_named=target_name,
                target_point_referenced="Revised rating to LEAN_HIRE (6/10) based on transactional cache bypass logic",
                stance="partially_agree",
                agreements=["Acknowledge Skeptic's score revision to LEAN_HIRE (6/10)."],
                disagreements=["Maintain that technical performance warrants 9/10 regardless of Skeptic's reference check conditions."],
                revised_rating=None,
                revised_score=None,
                updated_rationale=(
                    f"[Round 2] I note {target_name}'s score revision from 5/10 to 6/10 (LEAN_HIRE). While Skeptic remains cautious "
                    "and demands reference checks regarding resume wording, as Technical Lead I stand firm on my 9/10 (STRONG_HIRE) verdict. "
                    "Proven outage resolution under pressure and 50k RPS architecture remain the decisive technical benchmarks."
                )
            )
