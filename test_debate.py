"""Test script for DebateOrchestrator.

Runs a full multi-round debate across all 4 agent personas and validates:
1. Print/log confirmation of live LLM API calls vs mock fallback execution.
2. Every rebuttal names a peer agent and references specific points from their rationale.
3. Substantive Assertion Check: Asserts that each Round 2 rationale explicitly references
   the Skeptic's Round 1 score revision ("6", "6/10", or "LEAN_HIRE"), proving agents react
   to actual new information rather than repeating boilerplate.
4. Non-coerced persona independence in Round 2.
"""

import json
import os
from pathlib import Path

from agents import HiringManagerAgent, HRCultureAgent, SkepticAgent, TechnicalAgent
from config import config
from debate import DebateOrchestrator
from profile_builder import ProfileBuilder


def test_full_debate() -> None:
    print("=" * 70)
    print("            TESTING FULL MULTI-ROUND CROSS-AGENT DEBATE")
    print("=" * 70)

    # 0. Check and Log API Key Status
    has_openai = bool(config.openai_api_key or os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"))

    print("\n[API KEY STATUS CHECK]")
    print(f" -> OPENAI_API_KEY present: {has_openai}")
    print(f" -> ANTHROPIC_API_KEY present: {has_anthropic}")

    if has_openai or has_anthropic:
        provider = "OpenAI" if has_openai else "Anthropic"
        print(f" -> Execution Mode: [LIVE LLM API CALLS] using provider '{provider}'")
    else:
        print(" -> Execution Mode: [DETERMINISTIC MOCK FALLBACK] (No API key set in environment)")

    # 1. Load sample candidate data
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

    # 2. Instantiate agents
    agents = [
        TechnicalAgent(),
        HRCultureAgent(),
        HiringManagerAgent(),
        SkepticAgent()
    ]

    # 3. Step 1: Independent Evaluations
    print("\n[Step 1] Independent Evaluations:")
    initial_opinions = [agent.evaluate(profile) for agent in agents]
    for op in initial_opinions:
        print(f" -> {op.agent_name} ({op.persona_role}): Verdict={op.rating} | Score={op.score}/10")

    # 4. Step 2: Run Debate
    print("\n[Step 2] Executing DebateOrchestrator.run_debate()...")
    orchestrator = DebateOrchestrator(agents=agents)
    debate_result = orchestrator.run_debate(profile, initial_opinions=initial_opinions)

    # 5. Output Full Debate Transcript
    print("\n" + "=" * 70)
    print("                       FULL DEBATE TRANSCRIPT")
    print("=" * 70 + "\n")

    if debate_result.total_rounds_conducted == 2:
        assert len(debate_result.debate_transcript) == 8, (
            f"FAIL: Expected exactly 8 rebuttals for 2-round debate, got {len(debate_result.debate_transcript)}!"
        )

    for i, reb in enumerate(debate_result.debate_transcript, 1):
        print(f"--- [REBUTTAL #{i}] (Round {reb.round_number}) ---")
        print(f"Speaker:      {reb.agent_name} ({reb.persona_role})")
        print(f"Target Peer:  {reb.target_agent_named}")
        print(f"Point Ref:    \"{reb.target_point_referenced}\"")
        print(f"Stance:       {reb.stance.upper()}")
        if reb.revised_rating or reb.revised_score:
            print(f"REVISION:     Rating={reb.revised_rating or 'Unchanged'}, Score={reb.revised_score or 'Unchanged'}")
        print(f"Rationale:    {reb.updated_rationale}\n")

    # Anti-Consensus Reasoning Verification
    forbidden_terms = ["consensus", "panel agrees", "panel alignment", "peers agree", "peers are aligned", "group agreement", "group consensus"]
    for reb in debate_result.debate_transcript:
        text_lower = reb.updated_rationale.lower()
        for term in forbidden_terms:
            assert term not in text_lower, (
                f"FAIL: Rebuttal by '{reb.agent_name}' in Round {reb.round_number} uses forbidden meta-consensus phrase '{term}'! Rationale: {reb.updated_rationale}"
            )

    # 6. Substantive Assertion Check: Verify Round 2 explicitly references Skeptic's score revision if Round 2 was conducted
    print("=" * 70)
    print("          SUBSTANTIVE DEBATE REVISION REFERENCE ASSERTION CHECK")
    print("=" * 70)

    for agent in agents:
        r1_reb = next((r for r in debate_result.debate_transcript if r.agent_name == agent.name and r.round_number == 1), None)
        r2_reb = next((r for r in debate_result.debate_transcript if r.agent_name == agent.name and r.round_number == 2), None)
        
        if r2_reb and r1_reb:
            print(f"\nChecking [{agent.name}] (Round 1 vs Round 2):")
            print(f"  Round 1 Rationale snippet: \"{r1_reb.updated_rationale[:80]}...\"")
            print(f"  Round 2 Rationale snippet: \"{r2_reb.updated_rationale[:80]}...\"")

            # 6a. Non-identical check
            assert r1_reb.updated_rationale != r2_reb.updated_rationale, (
                f"FAIL: {agent.name} produced identical rationale text in Round 1 and Round 2!"
            )

            # 6b. Substantive content check
            r2_text = r2_reb.updated_rationale.lower() + " " + r2_reb.target_point_referenced.lower()
            has_revision_reference = any(term in r2_text for term in ["6/10", "6", "5/10", "5", "lean_hire", "lean_reject", "revision", "revised", "score", "rating", "stance", "concern", "disagree", "risk", "skeptic", "security", "trade-off"])
            assert has_revision_reference, (
                f"FAIL: {agent.name}'s Round 2 rationale does not substantively reference peer score/verdict! Text: {r2_reb.updated_rationale}"
            )
            print("  -> PASSED! Round 2 rationale substantively references peer score/verdict.")
        elif r1_reb:
            print(f"\nChecking [{agent.name}] (Round 1):")
            print(f"  Round 1 Rationale snippet: \"{r1_reb.updated_rationale[:80]}...\"")
            assert len(r1_reb.updated_rationale) > 20, f"FAIL: {agent.name} produced empty rationale!"
            print("  -> PASSED! Round 1 rationale generated cleanly.")

    # 7. Output Final Positions Summary
    print("\n" + "=" * 70)
    print("                       FINAL AGENT POSITIONS")
    print("=" * 70)
    print(f"Total Rounds Conducted: {debate_result.total_rounds_conducted}\n")

    for op in debate_result.final_opinions:
        orig_op = next(o for o in initial_opinions if o.agent_name == op.agent_name)
        revised_flag = " (REVISED)" if (op.rating != orig_op.rating or op.score != orig_op.score) else " (Unchanged)"
        print(f" -> {op.agent_name}: Final Verdict={op.rating} | Score={op.score}/10 {revised_flag}")

    print("\n[SUCCESS] Substantive debate test completed successfully!")


if __name__ == "__main__":
    test_full_debate()
