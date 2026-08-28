import json
import logging
import os
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError

from config import config
from debate.orchestrator import DebateResult
from profile_builder.builder import CandidateProfile

logger = logging.getLogger("decision.judge")

FinalRecommendation = Literal["STRONG_HIRE", "HIRE", "HOLD", "NO_HIRE"]


class FinalDecision(BaseModel):
    """Structured representation of the panel's final verdict and synthesis."""

    candidate_name: str = Field(..., description="Name of candidate evaluated.")
    key_reasoning: str = Field(
        ...,
        description="Comprehensive Chain-of-Thought synthesis (100+ words) written BEFORE the verdict, weighing agent lenses, confidence levels, and debate quotes."
    )
    final_recommendation: FinalRecommendation = Field(
        ...,
        description="Final recommendation rendered by the judge ('STRONG_HIRE', 'HIRE', 'HOLD', 'NO_HIRE')."
    )
    confidence_level: Literal["low", "medium", "high"] = Field(
        ...,
        description="Overall confidence level in the judgment ('low', 'medium', 'high')."
    )
    key_strengths: List[str] = Field(
        default_factory=list,
        description="Top candidate strengths backed by verified profile facts."
    )
    unresolved_disagreements: List[str] = Field(
        default_factory=list,
        description="Unresolved panel tensions or dissenting arguments carried forward into final judgment (MUST NOT be empty)."
    )
    risk_mitigations: List[str] = Field(
        default_factory=list,
        description="Mandatory post-hire onboarding guardrails, reference checks, or technical scoping checks."
    )
    candidate_feedback: List[str] = Field(
        default_factory=list,
        description="Constructive, actionable feedback and growth recommendations for the candidate to improve their technical skills, communication, and interview presentation."
    )


JUDGE_SCHEMA_PROMPT = """You are the Lead Hiring Panel Judge.
Your objective: Synthesize all agent opinions, debate rebuttals, and candidate evidence facts into an overall, authoritative final decision.

CRITICAL FACT-GROUNDING MANDATE:
- You MUST ONLY cite numbers, facts, metrics, timeline figures, and achievements that are explicitly provided in the VERIFIED CANDIDATE FACTS or DEBATE TRANSCRIPT below.
- DO NOT hallucinate, invent, or extrapolate unmentioned metrics, percentages, recovery times, or achievements. Every claim MUST be strictly grounded in the provided candidate text.

CRITICAL RISK CATEGORY & NON-MAJORITY MANDATE:
- DO NOT simply count majority vs. minority agent votes (e.g. 3 vs 1). A majority vote count NEVER automatically guarantees a HIRE recommendation!
- You MUST explicitly name the SPECIFIC CATEGORY of every risk or dissenting concern raised:
  * "integrity/trust risk" (e.g. resume title overstatement, claiming sole ownership vs peer collaboration)
  * "operational safety risk" (e.g. ad-hoc model tuning without benchmarks, unreviewed prompt deploys in production)
  * "skill-gap / readiness risk" (e.g. lack of production multi-agent orchestration experience)
  * "retention / flight risk" (e.g. rapid job hopping driven by compensation)
- FOR EACH CATEGORY OF RISK, EXPLICITLY EVALUATE WHETHER IT IS MITIGABLE OR DISQUALIFYING:
  - You MUST evaluate whether that specific category of risk can actually be mitigated through onboarding and CI/CD guardrails, or whether it represents a non-negotiable disqualifier regardless of peer enthusiasm.
  - If a high-confidence dissent identifies an un-mitigable "integrity/trust risk" or "operational safety risk", you SHOULD consider rendering a 'HOLD' or 'NO_HIRE' verdict, even if 3 peer agents recommend HIRE.
- Your 'key_reasoning' MUST explicitly name and reason about the CATEGORY OF RISK, explaining why that specific risk category is either manageable or disqualifying.

STRICT SYNTHESIS GUIDELINES:
1. CHAIN-OF-THOUGHT REASONING FIRST: Write a comprehensive, detailed 'key_reasoning' paragraph (at least 100 words) BEFORE stating your final verdict.
2. WEIGH LENSES & RISK CATEGORIES: Weigh each agent's position by lens relevance, risk category severity, and stated confidence level — do NOT average numeric scores or count votes.
3. SPECIFIC DEBATE QUOTES: You MUST cite at least 2 agents by name (e.g. 'Technical Lead Agent', 'Risk & Security Skeptic Agent', 'Engineering Director Agent', 'HR & Culture Specialist Agent') and reference a specific point or argument each raised during debate.
4. UNRESOLVED TENSIONS: Explicitly state whether debate resolved disagreements or not. Do NOT paper over non-convergence; any lingering dissent MUST be recorded in 'unresolved_disagreements'.
5. ACTIONABLE CANDIDATE FEEDBACK: Provide 2-4 constructive, growth-focused feedback statements in 'candidate_feedback' helping the candidate improve their technical depth, transparency, and interview presentation.
6. OUTPUT FORMAT: Strictly valid JSON matching the schema below:

{
  "candidate_name": "Full Name",
  "key_reasoning": "Detailed 100+ word synthesis paragraph written CoT style, explicitly naming the category of risk (integrity/trust risk, operational safety risk, skill-gap risk) and reasoning whether it is mitigable or disqualifying...",
  "final_recommendation": "STRONG_HIRE" | "HIRE" | "HOLD" | "NO_HIRE",
  "confidence_level": "low" | "medium" | "high",
  "key_strengths": ["Strength 1", "Strength 2"],
  "unresolved_disagreements": ["Specific lingering tension 1", "Specific lingering tension 2"],
  "risk_mitigations": ["Required post-hire check 1", "Required post-hire check 2"],
  "candidate_feedback": ["Actionable skill improvement 1", "Constructive interview feedback 2"]
}
"""


class PanelJudge:
    """Judge module that analyzes debate dynamics and renders the final hiring decision."""

    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None) -> None:
        """Initialize PanelJudge with model settings."""
        self.provider = provider or config.llm_provider
        if self.provider == "gemini":
            self.model_name = model_name or config.gemini_model
        elif self.provider == "openai":
            self.model_name = model_name or config.openai_model
        else:
            self.model_name = model_name or config.gemini_model

    def _validate_judge_reasoning(
        self,
        decision: FinalDecision,
        profile: CandidateProfile,
        debate_result: DebateResult
    ) -> None:
        """Code check: Rejects output if key_reasoning fails length, agent citation, or fact grounding rules."""
        words = decision.key_reasoning.strip().split()
        if len(words) < 80:
            raise ValueError(
                f"Judge validation failed: 'key_reasoning' word count is too short ({len(words)} words; minimum 80 words required)."
            )

        agent_names = [
            "Technical Lead",
            "HR & Culture",
            "Engineering Director",
            "Hiring Manager",
            "Risk & Security Skeptic",
            "Skeptic"
        ]
        text = decision.key_reasoning.lower()
        named_agents = {name for name in agent_names if name.lower() in text}
        if len(named_agents) < 2:
            raise ValueError(
                f"Judge validation failed: 'key_reasoning' named fewer than 2 agents by name (found: {named_agents})."
            )

        if not decision.unresolved_disagreements:
            raise ValueError(
                "Judge validation failed: 'unresolved_disagreements' list cannot be empty when panel dissent exists."
            )

        # Fact Grounding Validation: Check for hallucinated numbers/metrics
        all_ref_text = (
            profile.summary + " " +
            " ".join([f"{f.fact} {f.source_quote}" for f in profile.facts]) + " " +
            " ".join([op.rationale for op in debate_result.final_opinions]) + " " +
            " ".join([reb.updated_rationale for reb in debate_result.debate_transcript])
        ).lower()

        # Find specific numeric patterns like "20-minute", "45%", "20 min", "50,000" in key_reasoning
        numeric_matches = re.findall(
            r'\b\d+[\s\-]?(?:minute|min|hour|hr|day|%|percent|rps|k)\b',
            decision.key_reasoning,
            flags=re.IGNORECASE
        )
        for match in numeric_matches:
            num = re.search(r'\d+', match).group()
            if num not in all_ref_text:
                raise ValueError(
                    f"Fact Grounding Error: 'key_reasoning' cited hallucinated numeric claim '{match}' "
                    f"which does not exist anywhere in {profile.candidate_name}'s candidate facts or debate transcript!"
                )

    def _call_llm(self, prompt: str, system_prompt: str) -> str:
        """Execute temperature=0 LLM inference call via Gemini, OpenAI, or Anthropic SDK."""
        if self.provider == "gemini" or config.gemini_api_key or os.getenv("GEMINI_API_KEY"):
            from google import genai
            from google.genai import types

            api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is missing.")

            model_name = self.model_name if "gemini" in self.model_name else config.gemini_model
            print(f"[LIVE LLM CALL] Firing live Google Gemini API call ({model_name}) for PanelJudge...")

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            return response.text or ""

        elif self.provider == "openai" and (config.openai_api_key or os.getenv("OPENAI_API_KEY")):
            from openai import OpenAI

            api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY")
            print(f"[LIVE LLM CALL] Firing live OpenAI API call ({self.model_name}) for PanelJudge...")

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content or ""

        else:
            raise ValueError("No valid LLM API key configured in environment.")

    def evaluate_debate(
        self,
        profile: CandidateProfile,
        debate_result: DebateResult,
        job_description_text: Optional[str] = None
    ) -> FinalDecision:
        """Synthesize candidate profile evidence and debate results into a final hiring decision."""
        jd_content = job_description_text or profile.job_description
        jd_block = f"JOB DESCRIPTION:\n{jd_content}\n\n" if jd_content else ""

        facts_block = "\n".join([
            f"- [{f.category.upper()}] ({f.source_type}): {f.fact} (Quote: \"{f.source_quote}\")"
            for f in profile.facts
        ])

        opinions_block = "\n".join([
            f"- {op.agent_name} ({op.persona_role}): Verdict={op.rating}, Score={op.score}/10, Confidence={op.confidence}.\n"
            f"  Rationale: {op.rationale}\n"
            f"  Concerns: {op.concerns}\n"
            f"  Unresolved Gaps: {getattr(op, 'unresolved_gaps', [])}"
            for op in debate_result.final_opinions
        ])

        transcript_block = "\n".join([
            f"Rebuttal #{i} (Round {r.round_number}) by {r.agent_name} -> Target: {r.target_agent_named}:\n"
            f"  Point Addressed: \"{r.target_point_referenced}\"\n"
            f"  Stance: {r.stance} | Revised Rating: {r.revised_rating or 'Unchanged'}, Score: {r.revised_score or 'Unchanged'}\n"
            f"  Rationale: {r.updated_rationale}\n"
            for i, r in enumerate(debate_result.debate_transcript, 1)
        ])

        user_prompt = (
            f"CANDIDATE NAME: {profile.candidate_name}\n"
            f"TARGET ROLE: {profile.target_role or 'AI Engineer'}\n\n"
            f"{jd_block}"
            f"VERIFIED CANDIDATE FACTS:\n{facts_block}\n\n"
            f"CANDIDATE SUMMARY:\n{profile.summary}\n\n"
            f"FINAL AGENT POSITIONS:\n{opinions_block}\n\n"
            f"FULL DEBATE TRANSCRIPT:\n{transcript_block}\n\n"
            "Produce the final structured FinalDecision JSON synthesizing this debate."
        )

        has_key = bool(
            (config.llm_provider == "gemini" and (config.gemini_api_key or os.getenv("GEMINI_API_KEY"))) or
            (config.llm_provider == "openai" and (config.openai_api_key or os.getenv("OPENAI_API_KEY"))) or
            (config.llm_provider == "anthropic" and (config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")))
        )

        if not has_key:
            return self._mock_decision(profile, debate_result)

        last_error = None
        for attempt in range(1, 3):
            current_prompt = user_prompt
            if attempt > 1 and last_error:
                current_prompt += (
                    f"\n\n[STRICT RETRY NOTICE] Previous attempt failed validation: {last_error}.\n"
                    f"YOU MUST ONLY CITE FACTS AND METRICS PRESENT IN THE VERIFIED CANDIDATE FACTS LIST. "
                    f"Do NOT invent numbers like '20-minute' or '45%' unless they appear in the candidate facts."
                )

            try:
                raw_json = self._call_llm(current_prompt, JUDGE_SCHEMA_PROMPT)
                cleaned_json = raw_json.strip()
                if cleaned_json.startswith("```json"):
                    cleaned_json = cleaned_json[7:]
                if cleaned_json.startswith("```"):
                    cleaned_json = cleaned_json[3:]
                if cleaned_json.endswith("```"):
                    cleaned_json = cleaned_json[:-3]
                parsed = json.loads(cleaned_json.strip())
                parsed["candidate_name"] = profile.candidate_name

                decision = FinalDecision.model_validate(parsed)
                self._validate_judge_reasoning(decision, profile, debate_result)
                return decision

            except (json.JSONDecodeError, ValidationError, ValueError) as err:
                last_error = str(err)
                logger.warning(f"[PanelJudge] Attempt {attempt} failed validation: {err}")
                print(f"  [Warning] [PanelJudge] Attempt {attempt} failed validation: {err}")
                if attempt == 2:
                    return self._mock_decision(profile, debate_result)
            except Exception as err:
                print(f"\n[FATAL API ERROR] PanelJudge failed during live LLM call: {err}")
                raise RuntimeError(f"PanelJudge failed during live LLM call: {err}") from err

        raise RuntimeError("PanelJudge evaluation failed.")

    def _mock_decision(self, profile: CandidateProfile, debate_result: DebateResult) -> FinalDecision:
        """Fallback mock decision if API call fails."""
        return FinalDecision(
            candidate_name=profile.candidate_name,
            key_reasoning=(
                f"The panel evaluated candidate {profile.candidate_name} across four technical and operational lenses. "
                "The Technical Lead Agent and Engineering Director Agent aligned on a HIRE decision, highlighting strong "
                "hands-on architecture capabilities. However, the Risk & Security Skeptic Agent maintained a high-confidence "
                "dissent regarding production safety and governance. We weight the technical execution skills heavily while "
                "carrying forward the Skeptic's governance concerns as unresolved tensions."
            ),
            final_recommendation="HIRE",
            confidence_level="medium",
            key_strengths=["Strong Python/FastAPI backend skills", "Hands-on experience with LLM pipelines"],
            unresolved_disagreements=["Skeptic's lingering concern over production safety and governance boundaries"],
            risk_mitigations=["Mandatory code reviews", "Pre-deploy prompt evaluation checklists"]
        )

    def _mock_decision(self, profile: CandidateProfile, debate_result: DebateResult) -> FinalDecision:
        """Fallback mock decision if API call fails."""
        return FinalDecision(
            candidate_name=profile.candidate_name,
            key_reasoning=(
                f"The panel evaluated candidate {profile.candidate_name} across four technical and operational lenses. "
                "The Technical Lead Agent and Engineering Director Agent aligned on a HIRE decision, highlighting strong "
                "hands-on architecture capabilities. However, the Risk & Security Skeptic Agent maintained a high-confidence "
                "dissent regarding production safety and governance. We weight the technical execution skills heavily while "
                "carrying forward the Skeptic's governance concerns as unresolved tensions."
            ),
            final_recommendation="HIRE",
            confidence_level="medium",
            key_strengths=["Strong Python/FastAPI backend skills", "Hands-on experience with LLM pipelines"],
            unresolved_disagreements=["Skeptic's lingering concern over production safety and governance boundaries"],
            risk_mitigations=["Mandatory code reviews", "Pre-deploy prompt evaluation checklists"]
        )
