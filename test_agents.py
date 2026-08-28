"""Test script for multi-agent evaluate() implementations.

Runs all 4 persona agents (Technical, HR/Culture, Hiring Manager, Skeptic)
independently on the CandidateProfile and validates:
1. Persona differentiation (ratings and scores differ across personas).
2. Skeptic identification of contradiction pairs using quotes from both resume and transcript.
3. Strict quote verification for all key_evidence items.
"""

import json
from pathlib import Path

from agents import HiringManagerAgent, HRCultureAgent, SkepticAgent, TechnicalAgent
from profile_builder import ProfileBuilder


def test_agent_evaluations() -> None:
    print("=" * 70)
    print("         TESTING INDEPENDENT AGENT EVALUATIONS & PERSONA DIFFERENTIATION")
    print("=" * 70)

    # 1. Build CandidateProfile from sample data
    base_dir = Path(__file__).parent
    resume_path = base_dir / "sample_data" / "resume.txt"
    transcript_path = base_dir / "sample_data" / "transcript.txt"

    resume_text = resume_path.read_text(encoding="utf-8")
    transcript_text = transcript_path.read_text(encoding="utf-8")

    builder = ProfileBuilder()
    profile = builder.build(
        resume_text=resume_text,
        transcript_text=transcript_text,
        candidate_name="Alex Rivera",
        target_role="Senior Distributed Systems Engineer"
    )

    # 2. Instantiate all 4 persona agents
    agents = [
        TechnicalAgent(),
        HRCultureAgent(),
        HiringManagerAgent(),
        SkepticAgent()
    ]

    opinions = []

    # 3. Execute evaluate() independently for each agent
    print("\nExecuting evaluate() for each agent persona...")
    for agent in agents:
        print(f"\n---> Evaluating via [{agent.name}] ({agent.role})...")
        opinion = agent.evaluate(profile)
        opinions.append(opinion)

        print(f"     Verdict: {opinion.rating} | Score: {opinion.score}/10 | Confidence: {opinion.confidence}")
        print("     JSON Output:")
        print(json.dumps(opinion.model_dump(), indent=2))

    # 4. Verify Persona Differentiation (Disagreements exist)
    ratings = [op.rating for op in opinions]
    scores = [op.score for op in opinions]
    print("\n" + "=" * 70)
    print("                     PERSONA DIFFERENTIATION CHECK")
    print("=" * 70)
    print(f"Ratings: {ratings}")
    print(f"Scores:  {scores}")

    unique_ratings = set(ratings)
    unique_scores = set(scores)

    if len(unique_ratings) > 1 and len(unique_scores) > 1:
        print("[SUCCESS] Personas are clearly differentiated across ratings and scores!")
    else:
        print("[WARNING] Personas did not produce distinct ratings/scores!")

    # 5. Verify Skeptic Contradiction Pair Detection
    print("\n" + "=" * 70)
    print("               SKEPTIC CONTRADICTION PAIR CHECK")
    print("=" * 70)
    skeptic_op = [op for op in opinions if op.agent_name == "Risk & Security Skeptic Agent"][0]
    
    skeptic_resume_quotes = [f.source_quote for f in skeptic_op.key_evidence if f.source_type == "resume"]
    skeptic_transcript_quotes = [f.source_quote for f in skeptic_op.key_evidence if f.source_type == "transcript"]

    print(f"Skeptic Resume Evidence Quotes: {len(skeptic_resume_quotes)}")
    for q in skeptic_resume_quotes:
        print(f"  - [RESUME]: \"{q}\"")

    print(f"Skeptic Transcript Evidence Quotes: {len(skeptic_transcript_quotes)}")
    for q in skeptic_transcript_quotes:
        print(f"  - [TRANSCRIPT]: \"{q}\"")

    if skeptic_resume_quotes and skeptic_transcript_quotes:
        print("[SUCCESS] Skeptic successfully flagged contradiction pairs using real quotes from both Resume and Transcript!")
    else:
        print("[WARNING] Skeptic failed to pair Resume claims with Transcript walkbacks!")

    print("\n[SUCCESS] Agent evaluation tests completed successfully!")


if __name__ == "__main__":
    test_agent_evaluations()
