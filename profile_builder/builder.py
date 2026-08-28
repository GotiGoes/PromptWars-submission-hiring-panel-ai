"""Candidate profile extraction module.

Extracts structured, evidence-backed candidate facts from raw resume and interview transcript texts.
Each extracted fact tracks its source quote, source document type ('resume' vs 'transcript'),
and category for downstream agent consumption.

Includes LLM extraction with temperature=0, JSON schema guidance, automated retry logic on
parse/validation failure, and strict substring quote verification.
"""

import json
import logging
import os
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError

from config import config

logger = logging.getLogger("profile_builder")

SourceType = Literal["resume", "transcript"]
FactCategory = Literal[
    "technical_skill",
    "experience",
    "leadership_culture",
    "red_flag_concern",
    "unverifiable_claim",
    "education_background",
    "achievement"
]


class ExtractedFact(BaseModel):
    """Represents a single extracted fact paired with its source quote and origin document."""

    fact: str = Field(
        ...,
        description="The extracted factual statement, skill, experience, or observed trait."
    )
    source_quote: str = Field(
        ...,
        description="Exact quote from the source text supporting this fact. MUST be a direct verbatim substring."
    )
    source_type: SourceType = Field(
        ...,
        description="Origin document where the quote was observed ('resume' or 'transcript')."
    )
    category: FactCategory = Field(
        ...,
        description="Categorization of the fact for domain agent filtering."
    )
    confidence_notes: Optional[str] = Field(
        default=None,
        description="Optional notes regarding clarity, ambiguity, or context of the quote."
    )


class CandidateProfile(BaseModel):
    """Structured candidate profile containing facts linked to evidence quotes and source types."""

    candidate_name: str = Field(
        ...,
        description="Full name of the candidate."
    )
    target_role: Optional[str] = Field(
        default=None,
        description="Target job title or role being evaluated."
    )
    job_description: Optional[str] = Field(
        default=None,
        description="Full job description text for role-fit matching if available."
    )
    facts: List[ExtractedFact] = Field(
        default_factory=list,
        description="List of all extracted facts linked to quotes and source document types."
    )
    summary: str = Field(
        default="",
        description="High-level overview of the candidate's background."
    )

    def get_facts_by_category(self, category: FactCategory) -> List[ExtractedFact]:
        """Filter facts by a specific category (e.g. 'technical_skill', 'red_flag_concern')."""
        return [f for f in self.facts if f.category == category]

    def get_facts_by_source(self, source_type: SourceType) -> List[ExtractedFact]:
        """Filter facts by source document ('resume' or 'transcript')."""
        return [f for f in self.facts if f.source_type == source_type]


EXTRACTION_SCHEMA_PROMPT = """You are an expert HR and Technical Data Extraction AI.
Your task is to analyze a candidate's RESUME and INTERVIEW TRANSCRIPT and extract a structured set of evidence-backed facts into valid JSON.

You MUST follow these strict guidelines:
1. Every item in 'facts' must have an EXACT, VERBATIM 'source_quote' copied directly from either the RESUME or the TRANSCRIPT.
2. Do NOT paraphrase or alter the 'source_quote'. It will be strictly verified as a verbatim substring match against the raw source text in code.
3. Categorize each fact using one of the following exact categories:
   - "technical_skill": programming languages, tools, databases, frameworks, system architecture
   - "experience": past roles, projects, tasks performed, incident response
   - "leadership_culture": collaboration, disagreement handling, mentoring, team dynamics
   - "red_flag_concern": exaggerated/inflated claims, mistakes, architectural risks, short tenures
   - "unverifiable_claim": claims or answers that lack concrete numbers, metrics, or verifiable evidence (e.g. claiming a metric like override rate is 'low' without knowing the actual number, vague assertions, or unbacked performance claims)
   - "education_background": degrees, universities, certifications
   - "achievement": quantifiable results, latency reduction, throughput metrics, awards
4. Specify 'source_type' as either "resume" or "transcript".
5. CRITICAL REQUIREMENT FOR INFLATED CLAIMS: Do NOT merge resume claims and interview walkbacks/clarifications into a single fact. Extract the resume claim as a distinct fact (source_type: 'resume') and the transcript clarification as a separate distinct fact (source_type: 'transcript'). This allows panel agents to cross-reference and contrast claims against interview evidence.
6. CRITICAL REQUIREMENT FOR VAGUE / UNVERIFIABLE CLAIMS: You MUST extract statements where the candidate makes a claim but admits to lacking concrete metrics, data, or verified evidence (e.g. "We track override rate. It's low. I'd have to check the exact number though, haven't looked recently" or "No formal study, just tuned it as things broke"). DO NOT silently drop vague or unverifiable assertions; extract them as distinct facts under category "unverifiable_claim" or "red_flag_concern". The absence of concrete evidence/data IS the key fact worth capturing.
7. Provide a high-level candidate 'summary' and extract the candidate's name.

EXPECTED JSON SCHEMA FORMAT:
{
  "candidate_name": "Candidate Full Name",
  "target_role": "Target Role Title",
  "summary": "Brief overall summary",
  "facts": [
    {
      "fact": "Factual statement describing skill, experience, or observation",
      "source_quote": "EXACT verbatim substring from source text",
      "source_type": "transcript",
      "category": "unverifiable_claim",
      "confidence_notes": "Optional context notes"
    }
  ]
}
"""


class ProfileBuilder:
    """Builder service to parse resume and transcript texts into a structured CandidateProfile."""

    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None) -> None:
        """Initialize ProfileBuilder with model settings."""
        self.provider = provider or config.llm_provider
        if self.provider == "gemini":
            self.model_name = model_name or config.gemini_model
        elif self.provider == "openai":
            self.model_name = model_name or config.openai_model
        elif self.provider == "anthropic":
            self.model_name = model_name or config.anthropic_model
        else:
            self.model_name = model_name or config.gemini_model

    def _verify_quotes(
        self,
        profile: CandidateProfile,
        resume_text: str,
        transcript_text: str
    ) -> CandidateProfile:
        """Validate that every source_quote in the candidate profile is a verbatim substring match.

        Drops and logs any fact whose quote cannot be verified against the raw source document.
        """
        verified_facts: List[ExtractedFact] = []

        def normalize_ws(text: str) -> str:
            return re.sub(r'\s+', ' ', text).strip()

        norm_resume = normalize_ws(resume_text)
        norm_transcript = normalize_ws(transcript_text)

        for fact in profile.facts:
            quote = fact.source_quote.strip()
            if not quote:
                logger.warning(f"[Quote Verification Failed] Empty quote for fact: '{fact.fact}' - Dropping.")
                print(f"[Warning] [Quote Verification Failed] Empty quote for fact: '{fact.fact}' - Dropped.")
                continue

            target_raw = resume_text if fact.source_type == "resume" else transcript_text
            target_norm = norm_resume if fact.source_type == "resume" else norm_transcript

            is_valid = quote in target_raw
            if not is_valid:
                norm_quote = normalize_ws(quote)
                is_valid = norm_quote in target_norm

            if is_valid:
                verified_facts.append(fact)
            else:
                msg = (
                    f"[Warning] [Quote Verification Failed] Fact dropped due to unverified quote!\n"
                    f"   Fact: {fact.fact}\n"
                    f"   Quote: \"{fact.source_quote}\"\n"
                    f"   Source: {fact.source_type}"
                )
                logger.warning(msg)
                print(msg)

        profile.facts = verified_facts
        return profile

    def _call_llm(self, prompt: str, system_prompt: str) -> str:
        """Execute temperature=0 LLM inference call via Gemini, OpenAI, or Anthropic SDK."""
        if self.provider == "gemini" or config.gemini_api_key or os.getenv("GEMINI_API_KEY"):
            from google import genai
            from google.genai import types
            from google.genai.errors import ServerError, APIError

            api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is missing.")

            model_name = self.model_name if "gemini" in self.model_name else config.gemini_model
            print(f"[LIVE LLM CALL] Firing live Google Gemini API call ({model_name}) for ProfileBuilder...")

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
                    if call_attempt < 3 and ("503" in str(err) or "RESOURCE_EXHAUSTED" in str(err)):
                        import time
                        print(f"[Retry Warning] Gemini API spike ({err}). Retrying attempt {call_attempt + 1}/3 after 3 seconds...")
                        time.sleep(3)
                    else:
                        raise err
            raise last_err

        elif self.provider == "openai" or config.openai_api_key or os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is missing.")
            
            print(f"[LIVE LLM CALL] Firing live OpenAI API call ({self.model_name}) for ProfileBuilder...")
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

        elif self.provider == "anthropic" or config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"):
            from anthropic import Anthropic
            api_key = config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is missing.")

            print(f"[LIVE LLM CALL] Firing live Anthropic API call ({config.anthropic_model}) for ProfileBuilder...")
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
            raise ValueError("No valid LLM API key configured in environment.")

    def build(
        self,
        resume_text: str,
        transcript_text: str,
        candidate_name: str = "Alex Rivera",
        target_role: Optional[str] = None
    ) -> CandidateProfile:
        """Extract structured CandidateProfile with verbatim evidence quotes from resume and transcript."""
        user_prompt = (
            f"Candidate Name: {candidate_name}\n"
            f"Target Role: {target_role or 'Senior Software Engineer'}\n\n"
            f"--- RESUME ---\n{resume_text}\n\n"
            f"--- TRANSCRIPT ---\n{transcript_text}\n\n"
            "Extract all evidence-backed facts as a JSON object matching the requested schema."
        )

        system_prompt = EXTRACTION_SCHEMA_PROMPT
        last_error = None

        # Check if API key is present for active provider
        has_gemini_key = bool(config.gemini_api_key or os.getenv("GEMINI_API_KEY"))
        has_openai_key = bool(config.openai_api_key or os.getenv("OPENAI_API_KEY"))
        has_anthropic_key = bool(config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"))

        has_any_key = (
            (self.provider == "gemini" and has_gemini_key) or
            (self.provider == "openai" and has_openai_key) or
            (self.provider == "anthropic" and has_anthropic_key) or
            has_gemini_key or has_openai_key or has_anthropic_key
        )

        if not has_any_key:
            print("\n" + "=" * 80)
            print("  [ATTENTION] MOCK MODE ACTIVE: NO API KEY CONFIGURED FOR PROFILE BUILDER")
            print("  Using deterministic fallback extraction response for local testing.")
            print("=" * 80 + "\n")

        for attempt in range(1, 3):
            current_prompt = user_prompt
            if attempt > 1 and last_error:
                current_prompt += (
                    f"\n\n[ATTENTION: RETRY NOTICE]\n"
                    f"Your previous JSON response failed validation with the following error:\n{last_error}\n"
                    f"Please fix the error and output strictly valid JSON matching the schema."
                )

            try:
                if not has_any_key:
                    raw_json = self._mock_extraction_response(resume_text, transcript_text, candidate_name, target_role)
                else:
                    # Execute live API call. If it fails for ANY reason (auth, quota, network), raise loud error!
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
                profile = CandidateProfile.model_validate(parsed_data)

                profile = self._verify_quotes(profile, resume_text, transcript_text)
                return profile

            except (json.JSONDecodeError, ValidationError) as err:
                last_error = str(err)
                logger.warning(f"[ProfileBuilder] Attempt {attempt} JSON/Validation error: {err}")
                print(f"[Warning] [ProfileBuilder] Extraction attempt {attempt} failed schema validation: {err}")
                if attempt == 2:
                    raise RuntimeError(f"ProfileBuilder failed schema validation after 2 attempts. Last error: {err}") from err
            except Exception as err:
                # API errors, auth errors, network errors raise loud error immediately
                print(f"\n[FATAL API ERROR] Live LLM call failed for provider '{self.provider}': {err}")
                raise RuntimeError(f"[FATAL API ERROR] Live LLM call failed for provider '{self.provider}': {err}") from err

        raise RuntimeError("ProfileBuilder failed to extract profile.")

    def build_profile(
        self,
        candidate_name: str,
        resume_text: str,
        transcript_text: str,
        target_role: Optional[str] = None
    ) -> CandidateProfile:
        """Alias for build() for backwards compatibility with main.py."""
        return self.build(
            resume_text=resume_text,
            transcript_text=transcript_text,
            candidate_name=candidate_name,
            target_role=target_role
        )

    def _mock_extraction_response(
        self,
        resume_text: str,
        transcript_text: str,
        candidate_name: str,
        target_role: Optional[str]
    ) -> str:
        """Deterministic extracted JSON fallback when running without external API keys."""
        mock_data = {
            "candidate_name": candidate_name,
            "target_role": target_role or "Senior Backend Engineer",
            "summary": "Experienced distributed systems engineer with strong Go, Kafka, and PostgreSQL skills, but inflated claims regarding AI transformation.",
            "facts": [
                {
                    "fact": "Architected event-driven microservices handling 50,000+ RPS using Go, Apache Kafka, and Redis.",
                    "source_quote": "Architected event-driven microservices handling 50,000+ RPS using Go, Apache Kafka, and Redis.",
                    "source_type": "resume",
                    "category": "technical_skill",
                    "confidence_notes": "Direct resume claim verified by transcript performance discussion."
                },
                {
                    "fact": "Reduced database CPU utilization from 100% to 30% within 20 minutes by indexing slow queries and adding Redis caching.",
                    "source_quote": "I looked at our slow query logs and identified an unindexed complex JOIN query on our core orders table. I immediately implemented a Redis caching layer for hot read requests and added a composite index on PostgreSQL. Within 20 minutes, database CPU utilization dropped back down to 30%.",
                    "source_type": "transcript",
                    "category": "experience",
                    "confidence_notes": "Detailed incident response narrative in transcript."
                },
                {
                    "fact": "Claimed on resume to have spearheaded company-wide AI transformation across all engineering teams.",
                    "source_quote": "Spearheaded company-wide AI transformation across all engineering teams to revolutionize backend development velocity.",
                    "source_type": "resume",
                    "category": "achievement",
                    "confidence_notes": "Inflated resume achievement claim."
                },
                {
                    "fact": "Clarified in transcript that AI transformation was merely setting up Github Copilot and a small stack trace log summary wrapper script without formal team metrics.",
                    "source_quote": "I advocated for adopting Github Copilot and set up a basic internal wrapper script using OpenAI's API so developers could summarize log stack traces. It wasn't a formal team project with explicit metrics",
                    "source_type": "transcript",
                    "category": "red_flag_concern",
                    "confidence_notes": "Transcript walkback of resume claim."
                },
                {
                    "fact": "Claimed on resume to have single-handedly revamped entire infrastructure security posture and zero-trust framework.",
                    "source_quote": "Single-handedly revamped entire infrastructure security posture and zero-trust framework.",
                    "source_type": "resume",
                    "category": "achievement",
                    "confidence_notes": "Inflated resume claim."
                },
                {
                    "fact": "Clarified in transcript that security team led zero-trust strategy while candidate implemented microservices IAM roles and AWS Secrets Manager rotation.",
                    "source_quote": "The security team led the overall zero-trust strategy, but I handled the microservices IAM permissions implementation.",
                    "source_type": "transcript",
                    "category": "experience",
                    "confidence_notes": "Transcript clarification of security role."
                },
                {
                    "fact": "Demonstrated data-driven persuasion by building a 3x throughput benchmark prototype to align team on gRPC adoption.",
                    "source_quote": "I built a small benchmark prototype demonstrating a 3x throughput improvement, hosted a lunch-and-learn tech talk, and wrote clear setup documentation.",
                    "source_type": "transcript",
                    "category": "leadership_culture",
                    "confidence_notes": "Clear evidence of collaborative leadership."
                },
                {
                    "fact": "Admitted past mistake of insisting on self-managed EC2 Kubernetes clusters over managed cloud EKS.",
                    "source_quote": "I insisted on self-managing our custom Kubernetes clusters on EC2 instead of using managed Amazon EKS. We ended up spending an excessive amount of engineering time on control plane upgrades and cluster maintenance.",
                    "source_type": "transcript",
                    "category": "red_flag_concern",
                    "confidence_notes": "Self-aware reflection on operational mistake."
                },
                {
                    "fact": "Earned B.S. in Computer Science from UC Berkeley (2015 - 2019).",
                    "source_quote": "B.S. in Computer Science | University of California, Berkeley (2015 - 2019)",
                    "source_type": "resume",
                    "category": "education_background",
                    "confidence_notes": "Education claim on resume."
                },
                {
                    "fact": "Reduced PostgreSQL query latency by 45% through composite indexing and read-replica routing.",
                    "source_quote": "Reduced PostgreSQL query latency by 45% through composite indexing and read-replica routing.",
                    "source_type": "resume",
                    "category": "achievement",
                    "confidence_notes": "Quantifiable metric on resume."
                }
            ]
        }
        return json.dumps(mock_data)
