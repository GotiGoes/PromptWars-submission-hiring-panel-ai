"""Base agent module defining abstract persona interfaces and opinion data structures.

Enforces strict independence during initial evaluation: `evaluate()` accepts ONLY
CandidateProfile as input (no other_opinions parameter). Cross-agent reaction is
strictly isolated to `rebut()`.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError

from config import config
from profile_builder.builder import CandidateProfile, ExtractedFact

logger = logging.getLogger("agents")

RatingChoice = Literal["STRONG_HIRE", "HIRE", "LEAN_HIRE", "LEAN_REJECT", "REJECT"]
ConfidenceLevel = Literal["low", "medium", "high"]
StanceType = Literal["agree", "disagree", "partially_agree"]


class AgentOpinion(BaseModel):
    """Structured opinion output from an individual agent persona evaluation."""

    agent_name: str = Field(..., description="Name of the agent rendering the opinion.")
    persona_role: str = Field(..., description="Role description of the agent.")
    rating: RatingChoice = Field(..., description="Verdict / rating choice.")
    score: int = Field(..., ge=1, le=10, description="Numerical score from 1 to 10.")
    confidence: ConfidenceLevel = Field(..., description="Confidence level in verdict ('low', 'medium', 'high').")
    rationale: str = Field(..., description="Detailed rationale supporting the rating.")
    key_evidence: List[ExtractedFact] = Field(
        default_factory=list,
        description="Key extracted facts used as evidence for this verdict, pairing points with exact source quotes."
    )
    concerns: List[str] = Field(
        default_factory=list,
        description="List of specific concerns or red flags identified."
    )
    unresolved_gaps: List[str] = Field(
        default_factory=list,
        description="List of dimensions where evidence is insufficient or unverified (lowers confidence on that point, not an automatic score penalty)."
    )


class Rebuttal(BaseModel):
    """Represents an agent's reaction/rebuttal to peer opinions during debate rounds."""

    agent_name: str = Field(..., description="Name of the agent speaking.")
    persona_role: str = Field(..., description="Role of the agent.")
    round_number: int = Field(..., description="Debate round number (1 or 2).")
    target_agent_named: str = Field(..., description="Name of the peer agent being addressed.")
    target_point_referenced: str = Field(..., description="Specific point/quote from peer's rationale.")
    stance: Literal["agree", "disagree", "partially_agree"] = Field(..., description="Reaction stance.")
    agreements: List[str] = Field(default_factory=list, description="Points of agreement.")
    disagreements: List[str] = Field(default_factory=list, description="Points of disagreement.")
    revised_rating: Optional[RatingChoice] = Field(default=None, description="Updated rating if revised, else None.")
    revised_score: Optional[int] = Field(default=None, description="Updated score if revised, else None.")
    updated_rationale: str = Field(..., description="Full updated rationale text for this debate round.")


REBUTTAL_SCHEMA_PROMPT = """You are a hiring panel agent participating in a cross-agent debate round.
Analyze the provided peer agent opinions and output strictly valid JSON matching this EXACT schema:
{
  "agent_name": "Your Exact Agent Name",
  "persona_role": "Your Persona Role",
  "round_number": 1 or 2,
  "target_agent_named": "Full Name of the target peer agent you are reacting to",
  "target_point_referenced": "Specific point or rationale from the peer agent you are addressing",
  "stance": "agree" | "disagree" | "partially_agree",
  "agreements": ["Specific points you agree with"],
  "disagreements": ["Specific points you disagree with"],
  "revised_rating": "STRONG_HIRE" | "HIRE" | "LEAN_HIRE" | "LEAN_REJECT" | "REJECT" or null,
  "revised_score": 1 to 10 integer or null,
  "updated_rationale": "Detailed updated rationale explaining your position and reaction to the target peer agent"
}

CRITICAL REASONING RULE: You MUST NEVER cite "panel consensus", "consensus across the panel", "peers agree", "group alignment", "others think", or similar meta-references as a justification for your verdict or score. Every rebuttal must justify itself strictly using specific candidate evidence quotes/facts or your persona's domain criteria.
"""


class BaseAgent(ABC):
    """Abstract base class for all panel persona agents."""

    def __init__(self, name: str, role: str, model_name: str = "gpt-4o") -> None:
        """Initialize base agent with persona attributes and LLM model."""
        self.name = name
        self.role = role
        self.model_name = model_name

    @abstractmethod
    def get_persona_prompt(self) -> str:
        """Return the system prompt defining the persona's focus, tone, and evaluation criteria."""
        pass

    def _format_facts_without_confidence_notes(self, profile: CandidateProfile) -> str:
        """Format candidate facts for prompt without including pre-judged confidence_notes.

        Ensures agents evaluate raw facts and quotes without pre-judgment bias.
        """
        lines = [
            f"Candidate Name: {profile.candidate_name}",
            f"Target Role: {profile.target_role or 'Not Specified'}",
            f"Candidate Summary: {profile.summary}",
            "\nEXTRACTED FACTS & SOURCE QUOTES:"
        ]

        for i, fact in enumerate(profile.facts, 1):
            lines.append(f"Fact #{i}:")
            lines.append(f"  - Category: {fact.category}")
            lines.append(f"  - Source Type: {fact.source_type}")
            lines.append(f"  - Fact Statement: {fact.fact}")
            lines.append(f"  - Exact Source Quote: \"{fact.source_quote}\"")

        return "\n".join(lines)

    def _validate_evidence_quotes(self, opinion: AgentOpinion, profile: CandidateProfile) -> None:
        """Validate that every key_evidence item has a source_quote present in or matching profile.facts."""
        valid_quotes = [f.source_quote.strip() for f in profile.facts]
        
        for item in opinion.key_evidence:
            quote = item.source_quote.strip()
            if not quote:
                continue

            # Check if quote exists in valid_quotes or is a substring/superset of any valid quote
            is_valid = any(
                quote == v or quote in v or v in quote
                for v in valid_quotes
            )

            if not is_valid:
                logger.warning(
                    f"Evidence quote verification warning! Quote '{quote[:50]}...' not matched exactly in profile.facts."
                )

    def _call_llm(self, prompt: str, system_prompt: str) -> str:
        """Execute temperature=0 LLM inference call via Gemini, OpenAI, or Anthropic SDK."""
        provider = config.llm_provider

        if provider == "gemini" or config.gemini_api_key or os.getenv("GEMINI_API_KEY"):
            from google import genai
            from google.genai import types
            from google.genai.errors import ServerError, APIError

            api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is missing.")

            model_name = self.model_name if "gemini" in self.model_name else config.gemini_model
            print(f"[LIVE LLM CALL] Firing live Google Gemini API call ({model_name}) for agent '{self.name}'...")

            client = genai.Client(api_key=api_key)
            last_err = None
            for call_attempt in range(1, 4):
                try:
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
                except (ServerError, APIError, Exception) as err:
                    last_err = err
                    if call_attempt < 3 and "503" in str(err):
                        import time
                        print(f"[Retry Warning] Gemini 503 high demand spike encountered. Retrying attempt {call_attempt + 1}/3 after 3 seconds...")
                        time.sleep(3)
                    else:
                        raise err
            raise last_err

        elif provider == "openai" and (config.openai_api_key or os.getenv("OPENAI_API_KEY")):
            from openai import OpenAI
            api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY")
            print(f"[LIVE LLM CALL] Firing live OpenAI API call ({config.openai_model}) for agent '{self.name}'...")
            
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

        elif provider == "anthropic" and (config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")):
            from anthropic import Anthropic
            api_key = config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            print(f"[LIVE LLM CALL] Firing live Anthropic API call ({config.anthropic_model}) for agent '{self.name}'...")

            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model=config.anthropic_model,
                max_tokens=4096,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text

        else:
            print("\n" + "=" * 80)
            print(f"  [ATTENTION] MOCK MODE ACTIVE: NO API KEY CONFIGURED FOR PROVIDER '{provider.upper()}'")
            print(f"  Executing deterministic mock response for agent '{self.name}'.")
            print("=" * 80 + "\n")
            raise ValueError(f"No valid LLM API key configured for provider '{provider}'.")

    @abstractmethod
    def evaluate(
        self,
        profile: CandidateProfile,
        job_description_text: Optional[str] = None
    ) -> AgentOpinion:
        """Perform an independent evaluation of the candidate.

        NOTE: Enforced interface constraint — `evaluate()` accepts CandidateProfile and optional job description text.
        Inter-agent verdicts MUST NOT be passed to this method.

        Args:
            profile: The candidate profile with evidence facts.
            job_description_text: Optional role JD text context for role-matching agents.

        Returns:
            AgentOpinion containing initial verdict, score, confidence, rationale, evidence, and concerns.
        """
        pass

    @abstractmethod
    def rebut(
        self,
        profile: CandidateProfile,
        other_opinions: List[AgentOpinion],
        round_number: int = 1,
        job_description_text: Optional[str] = None
    ) -> Rebuttal:
        """React to peer agent opinions during debate round.

        Args:
            profile: CandidateProfile with extracted evidence facts.
            other_opinions: Full list of all OTHER agents' current opinions.
            round_number: Debate round index (1 or 2).
            job_description_text: Optional role JD text context for role-matching agents.

        Returns:
            Rebuttal with structured peer engagement and updated rationale.
        """
        pass
