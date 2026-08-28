"""Run live evaluation pipeline for Candidate A (Rohan Malhotra)."""

import json
from pathlib import Path
from agents import HiringManagerAgent, HRCultureAgent, SkepticAgent, TechnicalAgent
from config import config
from debate import DebateOrchestrator
from profile_builder import ProfileBuilder


def load_sample_file(file_path: Path) -> str:
    """Utility helper to load sample text files."""
    if not file_path.exists():
        raise FileNotFoundError(f"Sample data file not found at: {file_path}")
    return file_path.read_text(encoding="utf-8")


def main():
    print("=" * 80)
    print("      LIVE EVALUATION PIPELINE: CANDIDATE A (ROHAN MALHOTRA)")
    print("=" * 80)

    # 0. Validate Configuration
    config.validate_keys()
    active_model = config.gemini_model if config.llm_provider == "gemini" else config.openai_model
    print(f"\n[Config] Provider: {config.llm_provider} | Model: {active_model}")

    # 1. Load Input Data for Candidate A & Job Description
    base_dir = Path(__file__).parent / "sample_data"
    resume_path = base_dir / "candidate_a" / "resume.txt"
    transcript_path = base_dir / "candidate_a" / "transcript.txt"
    jd_path = base_dir / "job_description.txt"

    print("\n[Step 1] Loading Candidate A files & Job Description...")
    resume_text = load_sample_file(resume_path)
    transcript_text = load_sample_file(transcript_path)
    jd_text = load_sample_file(jd_path) if jd_path.exists() else None

    print(f" -> Resume: {resume_path} ({len(resume_text)} chars)")
    print(f" -> Transcript: {transcript_path} ({len(transcript_text)} chars)")
    print(f" -> Job Description: {jd_path} ({len(jd_text) if jd_text else 0} chars)")

    # Confirm JD context presence for HiringManager and Skeptic
    print("\n[CONFIRMATION] Job Description context loaded successfully:")
    print(f"  JD Title: {jd_text.splitlines()[0] if jd_text else 'None'}")
    print("  JD text will be threaded into HiringManagerAgent and SkepticAgent.")

    # 2. Build Profile via Live LLM Call
    print("\n" + "=" * 80)
    print("             STEP 2: EXTRACT CANDIDATE PROFILE")
    print("=" * 80)
    builder = ProfileBuilder(model_name=active_model)
    profile = builder.build(resume_text=resume_text, transcript_text=transcript_text)
    profile.candidate_name = "Rohan Malhotra"
    profile.target_role = "AI Engineer — Agentic Systems (Freight Operations)"
    profile.job_description = jd_text

    print("\n--- COMPLETE CANDIDATE PROFILE JSON ---")
    print(json.dumps(profile.model_dump(), indent=2))

    # 3. Independent Agent Evaluations (Phase 1)
    print("\n" + "=" * 80)
    print("          STEP 3: INDEPENDENT AGENT EVALUATIONS (PHASE 1)")
    print("=" * 80)
    agents = [
        TechnicalAgent(model_name=active_model),
        HRCultureAgent(model_name=active_model),
        HiringManagerAgent(model_name=active_model),
        SkepticAgent(model_name=active_model),
    ]

    initial_opinions = []
    for agent in agents:
        print(f"\n---> Independent Evaluation: [{agent.name}] ({agent.role})")
        op = agent.evaluate(profile, job_description_text=jd_text)
        initial_opinions.append(op)
        print(f"     Verdict: {op.rating} | Score: {op.score}/10 | Confidence: {op.confidence}")
        print(f"     Rationale:\n\"{op.rationale}\"")
        
        print("\n     [SEPARATION CHECK] Specific Concerns (Red Flags):")
        if op.concerns:
            for c in op.concerns:
                print(f"       - {c}")
        else:
            print("       - (None)")

        print("     [SEPARATION CHECK] Unresolved Gaps (Insufficient Info / Lowers Confidence):")
        if op.unresolved_gaps:
            for gap in op.unresolved_gaps:
                print(f"       - {gap}")
        else:
            print("       - (None)")

        print("\n     Key Evidence Quotes:")
        for ev in op.key_evidence:
            print(f"       - [{ev.source_type.upper()}]: \"{ev.source_quote}\"")

    # 4. Multi-Round Debate (Phase 2)
    print("\n" + "=" * 80)
    print("             STEP 4: MULTI-ROUND CROSS-AGENT DEBATE")
    print("=" * 80)
    orchestrator = DebateOrchestrator(agents=agents)
    debate_result = orchestrator.run_debate(profile, initial_opinions=initial_opinions, job_description_text=jd_text)

    # Confirm transcript count
    expected_rebuttals = 8 if debate_result.total_rounds_conducted == 2 else 4
    actual_rebuttals = len(debate_result.debate_transcript)
    print(f"\n[TRANSCRIPT COUNT CHECK] Expected: {expected_rebuttals} | Actual: {actual_rebuttals}")
    assert actual_rebuttals == expected_rebuttals, f"FAIL: Expected {expected_rebuttals} rebuttals, got {actual_rebuttals}!"
    print(" -> PASSED! Transcript count matches expected count.")

    print("\n" + "=" * 80)
    print("                       FULL DEBATE TRANSCRIPT")
    print("=" * 80 + "\n")

    for i, reb in enumerate(debate_result.debate_transcript, 1):
        print(f"--- [REBUTTAL #{i}] (Round {reb.round_number}) ---")
        print(f"Speaker:      {reb.agent_name} ({reb.persona_role})")
        print(f"Target Peer:  {reb.target_agent_named}")
        print(f"Point Ref:    \"{reb.target_point_referenced}\"")
        print(f"Stance:       {reb.stance.upper()}")
        if reb.revised_rating or reb.revised_score:
            print(f"REVISION:     Rating={reb.revised_rating or 'Unchanged'}, Score={reb.revised_score or 'Unchanged'}")
        print(f"Rationale:    {reb.updated_rationale}\n")

    # 5. Final Positions Summary
    print("=" * 80)
    print("                       FINAL AGENT POSITIONS")
    print("=" * 80)
    print(f"Total Rounds Conducted: {debate_result.total_rounds_conducted}\n")
    for op in debate_result.final_opinions:
        orig = next(o for o in initial_opinions if o.agent_name == op.agent_name)
        status = "REVISED" if (op.rating != orig.rating or op.score != orig.score) else "Unchanged"
        print(f" -> {op.agent_name}: Initial={orig.rating} ({orig.score}/10) | Final={op.rating} ({op.score}/10) [{status}]")

    # 6. Check Hiring Manager JD Line Quotes
    hm_op = next(o for o in initial_opinions if o.agent_name == "Engineering Director Agent")
    print("\n" + "=" * 80)
    print("          HIRING MANAGER JOB DESCRIPTION QUOTE CHECK")
    print("=" * 80)
    print("Hiring Manager Initial Rationale:")
    print(f"\"{hm_op.rationale}\"")

    jd_keywords = ["multi-agent", "python", "react", "freight", "rag", "vector search", "on-call", "production"]
    has_jd_quote = any(kw in hm_op.rationale.lower() for kw in jd_keywords)
    print(f"\n -> Contains explicit JD requirement comparison: {has_jd_quote}")

    print("\n[SUCCESS] Candidate A live evaluation complete!")


if __name__ == "__main__":
    main()
