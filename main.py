import argparse
import sys
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


def run_pipeline(candidate_dir_path: str = "sample_data/candidate_a") -> None:
    """Run the complete hiring panel evaluation workflow for a specific candidate directory."""
    candidate_path = Path(candidate_dir_path)
    if not candidate_path.is_absolute():
        candidate_path = Path(__file__).parent / candidate_path

    resume_file = candidate_path / "resume.txt"
    transcript_file = candidate_path / "transcript.txt"
    jd_file = Path(__file__).parent / "sample_data" / "job_description.txt"

    print("=" * 70)
    print(f"   HIRING PANEL AI - EVALUATION PIPELINE: [{candidate_path.name.upper()}]")
    print("=" * 70)

    # 0. Validate Configuration
    config.validate_keys()
    active_model = config.gemini_model if config.llm_provider == "gemini" else config.openai_model
    print(f"\n[Config] Provider: {config.llm_provider} | Model: {active_model}")

    # 1. Load Input Data
    print(f"\n[Step 1] Loading candidate data from: {candidate_path}...")
    resume_text = load_sample_file(resume_file)
    transcript_text = load_sample_file(transcript_file)
    jd_text = load_sample_file(jd_file) if jd_file.exists() else None

    # Derive candidate name from resume first line or folder
    first_line = resume_text.strip().splitlines()[0] if resume_text else candidate_path.name
    candidate_name = first_line.strip() if len(first_line) < 40 else candidate_path.name

    print(f"  -> Candidate: {candidate_name}")
    print(f"  -> Resume length: {len(resume_text)} chars")
    print(f"  -> Transcript length: {len(transcript_text)} chars")
    if jd_text:
        print(f"  -> Job Description loaded: {len(jd_text)} chars")

    # 2. Extract Candidate Profile with Fact Evidence
    print("\n[Step 2] Extracting evidence-backed candidate profile...")
    builder = ProfileBuilder(model_name=active_model)
    profile = builder.build(
        resume_text=resume_text,
        transcript_text=transcript_text
    )
    profile.candidate_name = candidate_name
    profile.target_role = "AI Engineer — Agentic Systems (Freight Operations)"
    profile.job_description = jd_text
    print(f" -> Extracted {len(profile.facts)} verified facts with source quotes.")

    # 3. Assemble Panel Agents
    print("\n[Step 3] Assembling multi-agent hiring panel...")
    agents = [
        TechnicalAgent(model_name=active_model),
        HRCultureAgent(model_name=active_model),
        HiringManagerAgent(model_name=active_model),
        SkepticAgent(model_name=active_model),
    ]
    for agent in agents:
        print(f" -> Joined: {agent.name} ({agent.role})")

    # 4. Conduct Cross-Agent Debate
    print("\n[Step 4] Running multi-stage panel debate...")
    orchestrator = DebateOrchestrator(agents=agents)
    initial_ops = [agent.evaluate(profile, job_description_text=jd_text) for agent in agents]
    debate_result = orchestrator.run_debate(profile, initial_opinions=initial_ops, job_description_text=jd_text)

    print("\n" + "=" * 70)
    print("                       DEBATE COMPLETE")
    print("=" * 70)
    print(f"Total Rounds: {debate_result.total_rounds_conducted}")
    print(f"Total Transcript Rebuttals: {len(debate_result.debate_transcript)}")
    for op in debate_result.final_opinions:
        print(f" -> {op.agent_name}: Final Verdict={op.rating} | Score={op.score}/10")

    # 5. Panel Judge Decision Synthesis
    print("\n[Step 5] Synthesizing final judgment via PanelJudge...")
    from decision import PanelJudge
    judge = PanelJudge(model_name=active_model)
    final_decision = judge.evaluate_debate(profile, debate_result, job_description_text=jd_text)

    print("\n" + "=" * 70)
    print("                    FINAL PANEL JUDGMENT")
    print("=" * 70)
    print(f"Candidate:            {final_decision.candidate_name}")
    print(f"Final Recommendation: {final_decision.final_recommendation}")
    print(f"Confidence Level:     {final_decision.confidence_level}")

    # 6. Generate & Save Markdown Report
    print("\n[Step 6] Generating and saving Markdown report...")
    from report.formatter import ReportFormatter
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    report_md = ReportFormatter.generate_markdown_report(
        profile=profile,
        initial_opinions=initial_ops,
        debate_result=debate_result,
        decision=final_decision
    )

    report_file = reports_dir / f"{candidate_path.name}_report.md"
    report_file.write_text(report_md, encoding="utf-8")
    print(f" -> Saved complete report to: {report_file}")


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "sample_data/candidate_a"
    run_pipeline(target_dir)

