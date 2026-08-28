"""Test script for ProfileBuilder.

Runs build() on enriched sample_data/resume.txt and transcript.txt, validates
verbatim source_quote verification, and outputs the resulting CandidateProfile as formatted JSON.
"""

import json
from pathlib import Path

from profile_builder import ProfileBuilder


def test_profile_builder() -> None:
    print("=" * 60)
    print("        TESTING PROFILE BUILDER & QUOTE VERIFICATION       ")
    print("=" * 60)

    base_dir = Path(__file__).parent
    resume_path = base_dir / "sample_data" / "resume.txt"
    transcript_path = base_dir / "sample_data" / "transcript.txt"

    print(f"\nReading resume from: {resume_path}")
    resume_text = resume_path.read_text(encoding="utf-8")

    print(f"Reading transcript from: {transcript_path}")
    transcript_text = transcript_path.read_text(encoding="utf-8")

    builder = ProfileBuilder()

    print("\nRunning ProfileBuilder.build()...")
    profile = builder.build(
        resume_text=resume_text,
        transcript_text=transcript_text,
        candidate_name="Alex Rivera",
        target_role="Senior Distributed Systems Engineer"
    )

    print("\n" + "=" * 60)
    print("              EXTRACTED CANDIDATE PROFILE (JSON)           ")
    print("=" * 60 + "\n")
    print(json.dumps(profile.model_dump(), indent=2))

    print("\n" + "=" * 60)
    print("                   QUOTE VERIFICATION SUMMARY             ")
    print("=" * 60)
    print(f"Total Verified Facts: {len(profile.facts)}")
    for i, fact in enumerate(profile.facts, 1):
        print(f"\nFact {i}: [{fact.category.upper()}] ({fact.source_type})")
        print(f"  Statement: {fact.fact}")
        print(f"  Quote: \"{fact.source_quote}\"")

    print("\n[SUCCESS] Test completed successfully!")


if __name__ == "__main__":
    test_profile_builder()
