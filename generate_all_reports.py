"""Generate rendered Markdown reports for Candidate A and Candidate B using ReportFormatter."""

import sys
from pathlib import Path

# Force UTF-8 encoding for stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from agents import HiringManagerAgent, HRCultureAgent, SkepticAgent, TechnicalAgent
from config import config
from debate import DebateOrchestrator
from decision import PanelJudge
from profile_builder import ProfileBuilder
from report import ReportFormatter


def load_sample_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def generate_candidate_report(candidate_dir_name: str, candidate_name: str):
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

    initial_opinions = [agent.evaluate(profile, job_description_text=jd_text) for agent in agents]

    # Step 3: Debate Orchestration
    orchestrator = DebateOrchestrator(agents=agents)
    debate_result = orchestrator.run_debate(profile, initial_opinions=initial_opinions, job_description_text=jd_text)

    # Step 4: Panel Judge Synthesis
    judge = PanelJudge(model_name=active_model)
    final_decision = judge.evaluate_debate(profile, debate_result, job_description_text=jd_text)

    # Step 5: Report Formatter
    report_md = ReportFormatter.generate_markdown_report(
        profile=profile,
        initial_opinions=initial_opinions,
        debate_result=debate_result,
        decision=final_decision
    )

    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / f"{candidate_dir_name}_report.md"
    report_file.write_text(report_md, encoding="utf-8")

    return report_file, report_md


def main():
    print("=" * 80)
    print("      GENERATING COMPLETE MARKDOWN REPORTS FOR BOTH CANDIDATES")
    print("=" * 80)

    print("\n[Processing Candidate A: Rohan Malhotra...]")
    file_a, md_a = generate_candidate_report("candidate_a", "Rohan Malhotra")
    print(f" -> Saved: {file_a}")

    print("\n[Processing Candidate B: Ananya Iyer...]")
    file_b, md_b = generate_candidate_report("candidate_b", "Ananya Iyer")
    print(f" -> Saved: {file_b}")

    print("\n" + "=" * 80)
    print("           RENDERED REPORT FOR CANDIDATE A (ROHAN MALHOTRA)")
    print("=" * 80 + "\n")
    print(md_a)

    print("\n" + "=" * 80)
    print("           RENDERED REPORT FOR CANDIDATE B (ANANYA IYER)")
    print("=" * 80 + "\n")
    print(md_b)


if __name__ == "__main__":
    main()
