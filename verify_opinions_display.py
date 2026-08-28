"""Verification script to confirm Agent Opinions cards show initial vs final positions side-by-side."""

import sys
from pathlib import Path
from profile_builder import ProfileBuilder
from agents import TechnicalAgent, HRCultureAgent, HiringManagerAgent, SkepticAgent
from debate import DebateOrchestrator
from config import config

sys.stdout.reconfigure(encoding="utf-8")

def main():
    print("=" * 80)
    print("  VERIFYING ROHAN MALHOTRA (CANDIDATE A) INITIAL VS FINAL AGENT POSITIONS")
    print("=" * 80)

    sample_dir = Path("sample_data/candidate_a")
    resume_text = (sample_dir / "resume.txt").read_text(encoding="utf-8")
    transcript_text = (sample_dir / "transcript.txt").read_text(encoding="utf-8")
    jd_text = (Path("sample_data/job_description.txt")).read_text(encoding="utf-8")

    active_model = config.gemini_model

    # 1. Profile
    builder = ProfileBuilder(model_name=active_model)
    profile = builder.build(resume_text=resume_text, transcript_text=transcript_text)
    profile.candidate_name = "Rohan Malhotra"
    profile.target_role = "AI Engineer — Agentic Systems (Freight Operations)"
    profile.job_description = jd_text

    # 2. Independent Agents
    agents = [
        TechnicalAgent(model_name=active_model),
        HRCultureAgent(model_name=active_model),
        HiringManagerAgent(model_name=active_model),
        SkepticAgent(model_name=active_model),
    ]

    initial_ops = [agent.evaluate(profile, job_description_text=jd_text) for agent in agents]

    # 3. Debate
    orchestrator = DebateOrchestrator(agents=agents)
    debate_res = orchestrator.run_debate(profile, initial_opinions=initial_ops, job_description_text=jd_text)

    print("\n--- AGENT OPINIONS CARD DISPLAY PRINTOUT ---")
    for op_init in initial_ops:
        op_final = next((o for o in debate_res.final_opinions if o.agent_name == op_init.agent_name), op_init)

        init_str = f"{op_init.rating} ({op_init.score}/10)"
        final_str = f"{op_final.rating} ({op_final.score}/10)"

        if op_init.score != op_final.score or op_init.rating != op_final.rating:
            badge = f"Initial: {init_str} ➔ Final: {final_str} (REVISED)"
        else:
            badge = f"Initial: {init_str} ➔ Final: {final_str} (Unchanged)"

        print(f"\n[{op_init.agent_name}]")
        print(f"  Badge Display: {badge}")
        print(f"  Pre-Debate Rationale: {op_init.rationale[:140]}...")

if __name__ == "__main__":
    main()
