"""Test ProfileBuilder for unverifiable claim extraction on Candidate A."""

import json
from pathlib import Path
from agents import HiringManagerAgent, HRCultureAgent, SkepticAgent, TechnicalAgent
from config import config
from profile_builder import ProfileBuilder


def load_sample_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def main():
    print("=" * 80)
    print("      TESTING PROFILE BUILDER FOR UNVERIFIABLE CLAIM EXTRACTION")
    print("=" * 80)

    config.validate_keys()
    active_model = config.gemini_model if config.llm_provider == "gemini" else config.openai_model

    base_dir = Path(__file__).parent / "sample_data"
    resume_path = base_dir / "candidate_a" / "resume.txt"
    transcript_path = base_dir / "candidate_a" / "transcript.txt"
    jd_path = base_dir / "job_description.txt"

    resume_text = load_sample_file(resume_path)
    transcript_text = load_sample_file(transcript_path)
    jd_text = load_sample_file(jd_path) if jd_path.exists() else None

    # Step 1: Re-run ProfileBuilder on Candidate A alone
    print("\n[Step 1] Running ProfileBuilder.build() on Candidate A...")
    builder = ProfileBuilder(model_name=active_model)
    profile = builder.build(resume_text=resume_text, transcript_text=transcript_text)
    profile.candidate_name = "Rohan Malhotra"
    profile.target_role = "AI Engineer — Agentic Systems (Freight Operations)"
    profile.job_description = jd_text

    print(f"\nExtracted Facts Count: {len(profile.facts)}")
    print("=" * 80)
    print("                  EXTRACTED FACTS & QUOTES")
    print("=" * 80)
    for i, fact in enumerate(profile.facts, 1):
        print(f"Fact #{i}: [{fact.category.upper()}] ({fact.source_type})")
        print(f"  Statement: {fact.fact}")
        print(f"  Quote:     \"{fact.source_quote}\"")

    # Step 2: Specific Check for Override Rate Transcript Line
    target_snippet = "override rate"
    found_override_fact = [f for f in profile.facts if target_snippet in f.source_quote.lower() or target_snippet in f.fact.lower()]

    print("\n" + "=" * 80)
    print("              OVERRIDE RATE FACT VERIFICATION CHECK")
    print("=" * 80)
    if found_override_fact:
        print(f"[SUCCESS] Override rate fact captured! Count: {len(found_override_fact)}")
        for f in found_override_fact:
            print(f"  - Category: {f.category}")
            print(f"  - Fact: {f.fact}")
            print(f"  - Quote: \"{f.source_quote}\"")
    else:
        print("[WARNING] Override rate fact was not captured in this run.")

    # Step 3: Run 4 Independent Agent Evaluations and check for references/concerns
    print("\n" + "=" * 80)
    print("    STEP 3: CHECKING INDEPENDENT AGENT OPINION CONCERNS & GAPS")
    print("=" * 80)
    agents = [
        TechnicalAgent(model_name=active_model),
        HRCultureAgent(model_name=active_model),
        HiringManagerAgent(model_name=active_model),
        SkepticAgent(model_name=active_model),
    ]

    for agent in agents:
        print(f"\n---> Evaluating via [{agent.name}] ({agent.role})...")
        op = agent.evaluate(profile, job_description_text=jd_text)
        print(f"     Verdict: {op.rating} | Score: {op.score}/10 | Confidence: {op.confidence}")
        print("     Concerns / Insufficient Evidence Fields:")
        if op.concerns:
            for c in op.concerns:
                print(f"       - {c}")
        else:
            print("       - (No explicit concerns listed)")

        has_override_ref = target_snippet in op.rationale.lower() or any(target_snippet in ev.source_quote.lower() for ev in op.key_evidence)
        print(f"     Explicitly references override rate / unverified metric: {has_override_ref}")


if __name__ == "__main__":
    main()
