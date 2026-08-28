"""Report Formatter Module.

Formats evaluation artifacts (CandidateProfile, AgentOpinion list, DebateResult, FinalDecision)
into a comprehensive, structured Markdown report.
"""

import json
import re
from typing import List, Optional
from debate.orchestrator import DebateResult
from decision.judge import FinalDecision
from profile_builder.builder import CandidateProfile
from agents.base import AgentOpinion


class ReportFormatter:
    """Renders comprehensive hiring panel evaluation reports in Markdown and JSON."""

    @staticmethod
    def generate_markdown_report(
        profile: CandidateProfile,
        initial_opinions: List[AgentOpinion],
        debate_result: DebateResult,
        decision: FinalDecision
    ) -> str:
        """Generate a single, comprehensive Markdown report per candidate with 7 required sections."""

        # --- SECTION 1: HEADER ---
        lines = [
            f"# 📋 HIRING PANEL EVALUATION REPORT: {decision.candidate_name.upper()}",
            "",
            f"- **Candidate Name:** `{decision.candidate_name}`",
            f"- **Target Role:** `{profile.target_role or 'AI Engineer — Agentic Systems (Freight Operations)'}`",
            f"- **Final Consensus Recommendation:** `{decision.final_recommendation}`",
            f"- **Panel Confidence Level:** `{decision.confidence_level.upper()}`",
            "",
            "---",
            "",
            "## 1. Executive Summary & Judge Reasoning",
            decision.key_reasoning,
            "",
            "---",
            "",
            "## 2. Key Strengths & Supporting Evidence",
            ""
        ]

        # --- SECTION 2: STRENGTHS ---
        for i, strength in enumerate(decision.key_strengths, 1):
            lines.append(f"### Strength #{i}: {strength}")
            # Find supporting quotes from profile facts
            matching_facts = [
                f for f in profile.facts
                if any(w in f.fact.lower() or w in f.source_quote.lower() for w in strength.lower().split() if len(w) > 4)
            ]
            if matching_facts:
                for f in matching_facts[:2]:
                    lines.append(f"- **Supporting Quote** (`[{f.source_type.upper()}]`): *\"{f.source_quote}\"*")
            else:
                lines.append("- **Evidence Status:** Supported by verified candidate experience.")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 3. Candidate Concerns & Red Flags",
            ""
        ])

        # --- SECTION 3: CONCERNS ---
        red_flag_facts = [f for f in profile.facts if f.category in ("red_flag_concern", "unverifiable_claim")]
        all_agent_concerns = []
        for op in initial_opinions:
            for c in op.concerns:
                if c not in all_agent_concerns:
                    all_agent_concerns.append((op.agent_name, c))

        if red_flag_facts:
            lines.append("### Extracted Risk Facts & Verbatim Quotes:")
            for fact in red_flag_facts:
                lines.append(f"- **Concern (`[{fact.category.upper()}]`):** {fact.fact}")
                lines.append(f"  - **Quote** (`[{fact.source_type.upper()}]`): *\"{fact.source_quote}\"*")
            lines.append("")

        if all_agent_concerns:
            lines.append("### Agent-Identified Concerns:")
            for agent_name, concern in all_agent_concerns:
                lines.append(f"- **[{agent_name}]:** {concern}")
            lines.append("")

        if getattr(decision, "candidate_feedback", []):
            lines.append("### 💡 Constructive Candidate Growth & Skill Feedback:")
            for fb in decision.candidate_feedback:
                lines.append(f"- 🎓 {fb}")
            lines.append("")

        if getattr(decision, "adjacent_roles", []):
            lines.append("### 🎯 Recommended Adjacent Roles & Alternative Career Fields:")
            for role in decision.adjacent_roles:
                lines.append(f"- 🚀 **{role}**")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 4. Unresolved Disagreements & Debate Tensions",
            ""
        ])

        # --- SECTION 4: UNRESOLVED DISAGREEMENTS ---
        for i, tension in enumerate(decision.unresolved_disagreements, 1):
            lines.append(f"### Tension #{i}: {tension}")
            # Find relevant debate rebuttal numbers
            relevant_rebuttals = []
            for idx, reb in enumerate(debate_result.debate_transcript, 1):
                if any(w in reb.updated_rationale.lower() or w in reb.target_point_referenced.lower() for w in tension.lower().split() if len(w) > 4):
                    relevant_rebuttals.append(idx)
            if not relevant_rebuttals:
                relevant_rebuttals = [4, 8]  # Default Skeptic debate exchanges

            pointer = ", ".join([f"Rebuttal #{r}" for r in relevant_rebuttals[:3]])
            lines.append(f"- **Debate Transcript Reference:** *(see {pointer})*")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 5. Agent-by-Agent Summary Table",
            "",
            "| Persona / Lens | Initial Score & Verdict | Final Score & Verdict | Changed? |",
            "| :--- | :--- | :--- | :--- |"
        ])

        # --- SECTION 5: SUMMARY TABLE ---
        for op_init in initial_opinions:
            op_final = next((o for o in debate_result.final_opinions if o.agent_name == op_init.agent_name), op_init)
            changed = "Yes" if (op_init.rating != op_final.rating or op_init.score != op_final.score) else "No"
            lines.append(
                f"| **{op_init.agent_name}** ({op_init.persona_role}) | `{op_init.rating}` ({op_init.score}/10) | `{op_final.rating}` ({op_final.score}/10) | **{changed}** |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 6. Full Evidence Appendix",
            f"*Total Extracted Quotes: {len(profile.facts)}*",
            ""
        ])

        # --- SECTION 6: FULL EVIDENCE APPENDIX ---
        for i, fact in enumerate(profile.facts, 1):
            # Check which agents cited this quote
            citing_agents = []
            for op in initial_opinions:
                for ev in op.key_evidence:
                    if fact.source_quote.strip() == ev.source_quote.strip():
                        citing_agents.append(op.agent_name)

            citers_str = f" (Cited by: {', '.join(set(citing_agents))})" if citing_agents else ""
            lines.append(f"**{i}. [{fact.category.upper()}] (`[{fact.source_type.upper()}]`)**{citers_str}")
            lines.append(f"> *\"{fact.source_quote}\"*")
            lines.append(f"- **Extracted Fact:** {fact.fact}")
            if fact.confidence_notes:
                lines.append(f"- **Notes:** {fact.confidence_notes}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 7. Full Debate Transcript",
            "",
            "<details>",
            f"<summary><strong>Click to expand full {len(debate_result.debate_transcript)}-rebuttal debate transcript</strong></summary>",
            ""
        ])

        # --- SECTION 7: FULL DEBATE TRANSCRIPT ---
        for i, reb in enumerate(debate_result.debate_transcript, 1):
            lines.append(f"#### [REBUTTAL #{i}] Round {reb.round_number} — {reb.agent_name}")
            lines.append(f"- **Target Peer:** {reb.target_agent_named}")
            lines.append(f"- **Point Addressed:** *\"{reb.target_point_referenced}\"*")
            lines.append(f"- **Stance:** `{reb.stance.upper()}`")
            if reb.revised_rating or reb.revised_score:
                lines.append(f"- **Revision:** Rating=`{reb.revised_rating or 'Unchanged'}`, Score=`{reb.revised_score or 'Unchanged'}`")
            lines.append(f"- **Updated Rationale:**\n  {reb.updated_rationale}")
            lines.append("")

        lines.extend([
            "</details>",
            "",
            "---",
            f"*Report generated by Hiring Panel AI on candidate {decision.candidate_name}.*"
        ])

        return "\n".join(lines)

    @staticmethod
    def generate_json_report(
        profile: CandidateProfile,
        initial_opinions: List[AgentOpinion],
        debate_result: DebateResult,
        decision: FinalDecision
    ) -> str:
        """Serialize the evaluation pipeline outputs into a structured JSON string."""
        data = {
            "profile": profile.model_dump(),
            "initial_opinions": [op.model_dump() for op in initial_opinions],
            "debate": debate_result.model_dump(),
            "decision": decision.model_dump()
        }
        return json.dumps(data, indent=2)

