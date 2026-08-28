from profile_builder.builder import ExtractedFact, CandidateProfile
from agents.base import AgentOpinion
from debate.orchestrator import Rebuttal, DebateResult
from decision.judge import PanelJudge


def build_synthetic_profile(name: str) -> CandidateProfile:
    return CandidateProfile(
        candidate_name=name,
        target_role="AI Engineer — Agentic Systems (Freight Operations)",
        job_description="Build production multi-agent systems for freight quoting and booking.",
        summary=f"{name} is an AI Engineer evaluated under synthetic stress test conditions.",
        facts=[
            ExtractedFact(
                category="technical_skill",
                fact="Built a production multi-agent logistics system handling 10k daily requests.",
                source_type="resume",
                source_quote="Built a production multi-agent logistics system handling 10k daily requests."
            ),
            ExtractedFact(
                category="red_flag_concern",
                fact="Overstated lead role on billing service migration.",
                source_type="transcript",
                source_quote="I claimed I led the migration, but it was primarily managed by a senior peer."
            )
        ]
    )


def run_unanimous_stress_test():
    print("\n" + "=" * 80)
    print("      STRESS TEST 1: UNANIMOUS 4-0 PANEL CONSENSUS (ALL AGENTS STRONG_HIRE)")
    print("=" * 80)

    profile = build_synthetic_profile("Elena Rostova")

    ops = [
        AgentOpinion(
            agent_name="Technical Lead Agent",
            persona_role="Technical Architecture Specialist",
            rating="STRONG_HIRE",
            score=9,
            confidence="high",
            rationale="Elena's multi-agent architecture handling 10k daily logistics requests proves elite technical competence.",
            key_evidence=[profile.facts[0]],
            concerns=[],
            unresolved_gaps=[]
        ),
        AgentOpinion(
            agent_name="HR & Culture Specialist Agent",
            persona_role="HR & Cultural Alignment Specialist",
            rating="STRONG_HIRE",
            score=9,
            confidence="high",
            rationale="Elena demonstrated total transparency during interviews and clear alignment with team values.",
            key_evidence=[profile.facts[0]],
            concerns=[],
            unresolved_gaps=[]
        ),
        AgentOpinion(
            agent_name="Engineering Director Agent",
            persona_role="Hiring Manager",
            rating="STRONG_HIRE",
            score=9,
            confidence="high",
            rationale="Elena matches all job description requirements and can immediately own freight agent workflows.",
            key_evidence=[profile.facts[0]],
            concerns=[],
            unresolved_gaps=[]
        ),
        AgentOpinion(
            agent_name="Risk & Security Skeptic Agent",
            persona_role="Risk & Security Skeptic",
            rating="STRONG_HIRE",
            score=9,
            confidence="high",
            rationale="Elena's multi-agent deployment includes strict tool-call validation and zero security incidents.",
            key_evidence=[profile.facts[0]],
            concerns=[],
            unresolved_gaps=[]
        )
    ]

    rebuttals = [
        Rebuttal(
            round_number=1,
            agent_name="Technical Lead Agent",
            persona_role="Technical Architecture Specialist",
            target_agent_named="Risk & Security Skeptic Agent",
            target_point_referenced="Elena's multi-agent deployment includes strict tool-call validation.",
            stance="agree",
            revised_rating="STRONG_HIRE",
            revised_score=9,
            updated_rationale="I fully agree with the Skeptic Agent. Her emphasis on tool-call security proves she is ready for production freight systems."
        )
    ]

    debate_res = DebateResult(
        candidate_name="Elena Rostova",
        initial_opinions=ops,
        final_opinions=ops,
        debate_transcript=rebuttals,
        total_rounds_conducted=1,
        convergence_reached=True
    )

    judge = PanelJudge()
    decision = judge.evaluate_debate(profile, debate_res)

    print(f"\nFinal Verdict:      {decision.final_recommendation}")
    print(f"Confidence Level:   {decision.confidence_level}")
    print(f"\nKey Reasoning:\n{decision.key_reasoning}")
    print(f"\nKey Strengths:             {decision.key_strengths}")
    print(f"Unresolved Disagreements:  {decision.unresolved_disagreements}")
    print(f"Risk Mitigations:          {decision.risk_mitigations}")


def run_deadlocked_2v2_stress_test():
    print("\n" + "=" * 80)
    print("      STRESS TEST 2: DEADLOCKED 2-VS-2 PANEL SPLIT (2 HIRE vs 2 REJECT)")
    print("=" * 80)

    profile = build_synthetic_profile("Marcus Vance")

    init_ops = [
        AgentOpinion(
            agent_name="Technical Lead Agent",
            persona_role="Technical Architecture Specialist",
            rating="HIRE",
            score=8,
            confidence="high",
            rationale="Marcus built a production multi-agent system handling 10k requests, proving deep technical skill.",
            key_evidence=[profile.facts[0]],
            concerns=[],
            unresolved_gaps=[]
        ),
        AgentOpinion(
            agent_name="Engineering Director Agent",
            persona_role="Hiring Manager",
            rating="HIRE",
            score=8,
            confidence="high",
            rationale="Marcus has the exact technical execution capability needed to deliver our freight quoting features.",
            key_evidence=[profile.facts[0]],
            concerns=[],
            unresolved_gaps=[]
        ),
        AgentOpinion(
            agent_name="HR & Culture Specialist Agent",
            persona_role="HR & Cultural Alignment Specialist",
            rating="REJECT",
            score=4,
            confidence="high",
            rationale="Marcus engaged in severe resume inflation regarding the billing migration, posing an unacceptable integrity/trust risk.",
            key_evidence=[profile.facts[1]],
            concerns=["Severe resume inflation on core project ownership."],
            unresolved_gaps=[]
        ),
        AgentOpinion(
            agent_name="Risk & Security Skeptic Agent",
            persona_role="Risk & Security Skeptic",
            rating="REJECT",
            score=4,
            confidence="high",
            rationale="Resume fabrication represents an un-mitigable integrity risk that compromises organizational trust and security posture.",
            key_evidence=[profile.facts[1]],
            concerns=["Un-mitigable integrity and trust risk."],
            unresolved_gaps=[]
        )
    ]

    rebuttals = [
        Rebuttal(
            round_number=1,
            agent_name="Technical Lead Agent",
            persona_role="Technical Architecture Specialist",
            target_agent_named="HR & Culture Specialist Agent",
            target_point_referenced="Marcus engaged in severe resume inflation posing an unacceptable integrity/trust risk.",
            stance="disagree",
            revised_rating="HIRE",
            revised_score=8,
            updated_rationale="While I acknowledge the billing claim inflation, his hands-on coding skill in multi-agent logistics outweighs this interview stumble."
        ),
        Rebuttal(
            round_number=1,
            agent_name="Risk & Security Skeptic Agent",
            persona_role="Risk & Security Skeptic",
            target_agent_named="Technical Lead Agent",
            target_point_referenced="His hands-on coding skill in multi-agent logistics outweighs this interview stumble.",
            stance="disagree",
            revised_rating="REJECT",
            revised_score=4,
            updated_rationale="Technical skills cannot override fundamental integrity failure. Overstating project leadership is an un-mitigable integrity/trust risk that disqualifies a candidate."
        )
    ]

    debate_res = DebateResult(
        candidate_name="Marcus Vance",
        initial_opinions=init_ops,
        final_opinions=init_ops,
        debate_transcript=rebuttals,
        total_rounds_conducted=1,
        convergence_reached=False
    )

    judge = PanelJudge()
    decision = judge.evaluate_debate(profile, debate_res)

    print(f"\nFinal Verdict:      {decision.final_recommendation}")
    print(f"Confidence Level:   {decision.confidence_level}")
    print(f"\nKey Reasoning:\n{decision.key_reasoning}")
    print(f"\nKey Strengths:             {decision.key_strengths}")
    print(f"Unresolved Disagreements:  {decision.unresolved_disagreements}")
    print(f"Risk Mitigations:          {decision.risk_mitigations}")


def main():
    run_unanimous_stress_test()
    run_deadlocked_2v2_stress_test()


if __name__ == "__main__":
    main()

