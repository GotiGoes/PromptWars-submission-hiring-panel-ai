"""Run PanelJudge.evaluate_debate() on both Candidate A and Candidate B and display side-by-side judgment comparison."""

import json
from pathlib import Path
from agents import HiringManagerAgent, HRCultureAgent, SkepticAgent, TechnicalAgent
from config import config
from debate import DebateOrchestrator
from decision import PanelJudge
from profile_builder import ProfileBuilder


def load_sample_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def evaluate_candidate(candidate_dir_name: str, candidate_name: str):
    """Run full pipeline for a candidate up to PanelJudge."""
    config.validate_keys()
    active_model = config.gemini_model if config.llm_provider == "gemini" else config.openai_model

    base_dir = Path(__file__).parent / "sample_data"
    resume_path = base_dir / candidate_dir_name / "resume.txt"
    transcript_path = base_dir / candidate_dir_name / "transcript.txt"
    jd_path = base_dir / "job_description.txt"

    resume_text = load_sample_file(resume_path)
    transcript_text = load_sample_file(transcript_path)
    jd_text = load_sample_file(jd_path) if jd_path.exists() else None

    # Step 1: Profile Builder
    builder = ProfileBuilder(model_name=active_model)
    profile = builder.build(resume_text=resume_text, transcript_text=transcript_text)
    profile.candidate_name = candidate_name
    profile.target_role = "AI Engineer — Agentic Systems (Freight Operations)"
    profile.job_description = jd_text

    # Step 2: 4 Agent Independent Evaluations
    agents = [
        TechnicalAgent(model_name=active_model),
        HRCultureAgent(model_name=active_model),
        HiringManagerAgent(model_name=active_model),
        SkepticAgent(model_name=active_model),
    ]

    initial_opinions = []
    for agent in agents:
        op = agent.evaluate(profile, job_description_text=jd_text)
        initial_opinions.append(op)

    # Step 3: Debate Orchestration
    orchestrator = DebateOrchestrator(agents=agents)
    debate_result = orchestrator.run_debate(profile, initial_opinions=initial_opinions, job_description_text=jd_text)

    # Step 4: Panel Judge Synthesis
    judge = PanelJudge(model_name=active_model)
    final_decision = judge.evaluate_debate(profile, debate_result, job_description_text=jd_text)

    return profile, debate_result, final_decision


def main():
    print("=" * 80)
    print("      PANEL JUDGE SYNTHESIS: CANDIDATE A vs CANDIDATE B SIDE-BY-SIDE")
    print("=" * 80)

    print("\n[Executing Candidate A: Rohan Malhotra...]")
    prof_a, deb_a, dec_a = evaluate_candidate("candidate_a", "Rohan Malhotra")

    print("\n[Executing Candidate B: Ananya Iyer...]")
    prof_b, deb_b, dec_b = evaluate_candidate("candidate_b", "Ananya Iyer")

    print("\n" + "=" * 80)
    print("                     SIDE-BY-SIDE JUDGMENT COMPARISON")
    print("=" * 80 + "\n")

    print(f"{'Metric / Field':<30} | {'Candidate A (Rohan Malhotra)':<40} | {'Candidate B (Ananya Iyer)':<40}")
    print("-" * 115)
    print(f"{'Final Recommendation':<30} | {dec_a.final_recommendation:<40} | {dec_b.final_recommendation:<40}")
    print(f"{'Confidence Level':<30} | {dec_a.confidence_level:<40} | {dec_b.confidence_level:<40}")

    print("\n" + "=" * 80)
    print("                  CANDIDATE A (ROHAN MALHOTRA) JUDGMENT DETAILS")
    print("=" * 80)
    print(f"Verdict:             {dec_a.final_recommendation}")
    print(f"Confidence Level:    {dec_a.confidence_level}")
    print(f"\nKey Reasoning (Chain-of-Thought Synthesis):\n\"{dec_a.key_reasoning}\"\n")
    print("Key Strengths:")
    for s in dec_a.key_strengths:
        print(f"  - {s}")
    print("\nUnresolved Panel Disagreements / Tensions:")
    for u in dec_a.unresolved_disagreements:
        print(f"  - {u}")
    print("\nRequired Risk Mitigations:")
    for m in dec_a.risk_mitigations:
        print(f"  - {m}")

    print("\n" + "=" * 80)
    print("                  CANDIDATE B (ANANYA IYER) JUDGMENT DETAILS")
    print("=" * 80)
    print(f"Verdict:             {dec_b.final_recommendation}")
    print(f"Confidence Level:    {dec_b.confidence_level}")
    print(f"\nKey Reasoning (Chain-of-Thought Synthesis):\n\"{dec_b.key_reasoning}\"\n")
    print("Key Strengths:")
    for s in dec_b.key_strengths:
        print(f"  - {s}")
    print("\nUnresolved Panel Disagreements / Tensions:")
    for u in dec_b.unresolved_disagreements:
        print(f"  - {u}")
    print("\nRequired Risk Mitigations:")
    for m in dec_b.risk_mitigations:
        print(f"  - {m}")


if __name__ == "__main__":
    main()
