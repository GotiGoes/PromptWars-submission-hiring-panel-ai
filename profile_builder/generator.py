"""Synthetic Candidate Generator module.

Generates realistic candidate resumes and interview transcripts using Gemini API based on a prompt or archetype.
"""

import json
import logging
import os
from typing import Tuple, Optional
from pydantic import BaseModel, Field

from config import config

logger = logging.getLogger("candidate_generator")


class SyntheticCandidateOutput(BaseModel):
    """Schema for AI-generated synthetic candidate documents."""
    candidate_name: str = Field(..., description="Full candidate name.")
    resume_text: str = Field(..., description="Complete, detailed professional resume text.")
    transcript_text: str = Field(..., description="Complete, multi-turn interview transcript text.")


GENERATOR_PROMPT = """You are an expert HR and Engineering Recruiter for Freight-Tech AI systems.
Your task is to generate a realistic candidate profile (Resume and Interview Transcript) matching the requested archetype and target role.

Target Role: {target_role}
Requested Candidate Archetype: {archetype}

GENERATION RULES:
1. Candidate Name: Create a realistic full name.
2. Resume: Write a detailed resume (summary, 2-3 past roles with bullet points, metrics, tech stack). Include both strong technical achievements and 1-2 realistic nuances or gaps matching the archetype.
3. Interview Transcript: Write a realistic 6-8 turn interview transcript between 'Interviewer' and the candidate. Make the conversation natural, probing technical depth, incident responses, ownership, and specific metrics.

Output MUST be strictly valid JSON matching this schema:
{{
  "candidate_name": "Full Name",
  "resume_text": "Full resume content...",
  "transcript_text": "Interviewer: ...\\nCandidate: ..."
}}
"""


class CandidateGenerator:
    """Uses Gemini API to generate synthetic candidate resumes and transcripts."""

    def __init__(self, model_name: Optional[str] = None):
        self.provider = config.llm_provider
        self.model_name = model_name or config.gemini_model

    def generate_candidate(
        self,
        archetype: str,
        target_role: str = "AI Engineer — Agentic Systems (Freight Operations)"
    ) -> Tuple[str, str, str]:
        """Generate (candidate_name, resume_text, transcript_text) using Gemini API."""
        prompt = GENERATOR_PROMPT.format(archetype=archetype, target_role=target_role)

        if self.provider == "gemini":
            from google import genai
            from google.genai import types

            api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY")
            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                )
            )
            data = json.loads(response.text)
            parsed = SyntheticCandidateOutput(**data)
            return parsed.candidate_name, parsed.resume_text, parsed.transcript_text
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented for candidate generator.")
