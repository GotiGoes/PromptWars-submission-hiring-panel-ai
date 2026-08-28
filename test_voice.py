"""Test script for VoiceDebateGenerator."""

from pathlib import Path
from debate.orchestrator import Rebuttal, DebateResult
from debate.voice import VoiceDebateGenerator


def main():
    rebs = [
        Rebuttal(
            round_number=1,
            agent_name="Technical Lead Agent",
            persona_role="Technical Architecture Specialist",
            target_agent_named="Risk & Security Skeptic Agent",
            target_point_referenced="Production multi-agent experience",
            stance="agree",
            revised_rating="HIRE",
            revised_score=8,
            updated_rationale="I agree with the Skeptic Agent that production security is essential for freight operations."
        ),
        Rebuttal(
            round_number=1,
            agent_name="Risk & Security Skeptic Agent",
            persona_role="Risk & Security Skeptic",
            target_agent_named="Technical Lead Agent",
            target_point_referenced="Foundational microservices experience",
            stance="disagree",
            revised_rating="LEAN_REJECT",
            revised_score=5,
            updated_rationale="I disagree. Single-turn microservices do not provide adequate protection against recursive agent loops."
        )
    ]

    debate_res = DebateResult(
        candidate_name="Test Candidate",
        initial_opinions=[],
        final_opinions=[],
        debate_transcript=rebs,
        total_rounds_conducted=1,
        convergence_reached=True
    )

    out_file = Path("reports/test_debate.wav")
    result = VoiceDebateGenerator.generate_debate_audio(debate_res, out_file)

    if result and out_file.exists():
        print(f"[SUCCESS] Voice audio generated at {out_file} (Size: {out_file.stat().st_size} bytes)")
    else:
        print("[NOTICE] Voice synthesis skipped or unavailable.")


if __name__ == "__main__":
    main()
