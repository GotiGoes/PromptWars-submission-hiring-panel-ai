"""Streamlit Web Interface for Hiring Panel AI Evaluation Pipeline.

Polished visual presentation featuring:
- Dynamic candidate selection cards
- 5-stage visual progress tracker
- 4 restructured output tabs (Summary, Agent Opinions, Debate, Full Report)
- Consistent persona color-coding across all views
- Download report functionality and idle state welcome panel
"""

import logging
import os
from pathlib import Path
import streamlit as st

from config import config
from profile_builder import ProfileBuilder
from agents import TechnicalAgent, HRCultureAgent, HiringManagerAgent, SkepticAgent
from debate import DebateOrchestrator
from decision import PanelJudge
from report import ReportFormatter

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Hiring Panel AI",
    page_icon="🧑‍💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PERSONA COLOR SYSTEM & ICONS ---
PERSONA_CONFIG = {
    "Technical Lead Agent": {"color": "#1E88E5", "icon": "🛠️", "badge": "🔵", "role": "Technical Evaluator"},
    "HR & Culture Specialist Agent": {"color": "#43A047", "icon": "👥", "badge": "🟢", "role": "HR & Culture Evaluator"},
    "Engineering Director Agent": {"color": "#8E24AA", "icon": "👔", "badge": "🟣", "role": "Hiring Manager"},
    "Risk & Security Skeptic Agent": {"color": "#E53935", "icon": "🕵️", "badge": "🔴", "role": "Devil's Advocate"},
}

VERDICT_COLORS = {
    "STRONG_HIRE": "#2E7D32",   # Dark Green
    "HIRE": "#43A047",          # Green
    "LEAN_HIRE": "#F57C00",     # Orange/Yellow
    "HOLD": "#F57C00",          # Orange
    "LEAN_REJECT": "#D32F2F",   # Red
    "REJECT": "#C62828",        # Deep Red
    "NO_HIRE": "#B71C1C",       # Dark Red
}


def discover_candidates(sample_data_dir: Path) -> dict:
    """Scan sample_data directory for candidate folders containing resume.txt and transcript.txt."""
    candidates = {}
    if not sample_data_dir.exists():
        return candidates

    for item in sorted(sample_data_dir.iterdir()):
        if item.is_dir():
            resume = item / "resume.txt"
            transcript = item / "transcript.txt"
            if resume.exists() and transcript.exists():
                first_line = resume.read_text(encoding="utf-8").strip().splitlines()[0]
                name = first_line.strip() if len(first_line) < 40 else item.name.replace("_", " ").title()
                candidates[f"{name} ({item.name})"] = item
    return candidates


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_step_tracker(current_step: int, active_detail: str):
    """Render horizontal visual progress step tracker."""
    steps = [
        ("1. Profile", "📄"),
        ("2. Opinions", "🕵️"),
        ("3. Debate", "🗣️"),
        ("4. Judge", "⚖️"),
        ("5. Report", "📊")
    ]
    cols = st.columns(5)
    for idx, (label, icon) in enumerate(steps, 1):
        with cols[idx - 1]:
            if idx < current_step:
                st.markdown(
                    f"<div style='background-color:#E8F5E9; border-left:4px solid #43A047; padding:8px; border-radius:4px; font-size:14px;'>"
                    f"<b>✓ {icon} {label}</b></div>",
                    unsafe_allow_html=True
                )
            elif idx == current_step:
                st.markdown(
                    f"<div style='background-color:#E3F2FD; border-left:4px solid #1E88E5; padding:8px; border-radius:4px; font-size:14px;'>"
                    f"<b>⏳ {icon} {label}</b></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='background-color:#F5F5F5; border-left:4px solid #B0BEC5; padding:8px; border-radius:4px; font-size:14px; color:#757575;'>"
                    f"{icon} {label}</div>",
                    unsafe_allow_html=True
                )
    st.caption(f"**Current Progress:** {active_detail}")


def main():
    # --- SIDEBAR CONFIG & METADATA ---
    st.sidebar.title("🧑‍💼 Hiring Panel AI")
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Configuration")

    provider = config.llm_provider.upper()
    active_model = config.gemini_model if config.llm_provider == "gemini" else config.openai_model
    has_key = bool(config.gemini_api_key or os.getenv("GEMINI_API_KEY") or config.openai_api_key)

    st.sidebar.info(f"**LLM Provider:** `{provider}`\n\n**Active Model:** `{active_model}`")

    if has_key:
        st.sidebar.success("✅ **Live API Key Configured** (Real LLM Calls Active)")
    else:
        st.sidebar.warning("⚠️ **Mock Mode Active** (No API Key Detected)")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Persona Color Guide")
    for persona, cfg in PERSONA_CONFIG.items():
        st.sidebar.markdown(
            f"<div style='border-left:4px solid {cfg['color']}; padding-left:8px; margin-bottom:6px;'>"
            f"<b>{cfg['icon']} {persona.replace(' Agent', '')}</b><br><small>{cfg['role']}</small></div>",
            unsafe_allow_html=True
        )

    # --- MAIN TITLE & SUBTITLE ---
    st.title("🧑‍💼 Autonomous Multi-Agent Hiring Panel")
    st.markdown("##### *4 AI agents independently evaluate a candidate, debate their findings, and reach an evidence-weighted decision.*")
    st.markdown("---")

    # --- CANDIDATE SELECTION CARDS ---
    sample_data_dir = Path(__file__).parent / "sample_data"
    candidates = discover_candidates(sample_data_dir)

    if not candidates:
        st.error("No valid candidate directories found in `sample_data/` containing `resume.txt` and `transcript.txt`.")
        return

    st.subheader("📋 Candidate Selection")

    if "selected_candidate_key" not in st.session_state and candidates:
        st.session_state["selected_candidate_key"] = list(candidates.keys())[0]

    selected_candidate_key = st.session_state["selected_candidate_key"]

    cand_cols = st.columns(max(len(candidates), 1))
    for idx, (label, folder_path) in enumerate(candidates.items()):
        c_name = label.split(" (")[0]
        c_id = folder_path.name
        is_selected = (label == selected_candidate_key)

        with cand_cols[idx % len(cand_cols)]:
            border_color = "#1E88E5" if is_selected else "#E0E0E0"
            bg_color = "#F0F4F8" if is_selected else "#FFFFFF"
            st.markdown(
                f"<div style='border:2px solid {border_color}; background-color:{bg_color}; padding:14px; border-radius:8px; margin-bottom:10px;'>"
                f"<h4 style='margin:0; color:#1A237E;'>{c_name}</h4>"
                f"<p style='margin:4px 0; font-size:13px; color:#555;'>📁 <code>sample_data/{c_id}</code></p>"
                f"<p style='margin:0; font-size:13px;'><b>Target:</b> AI Engineer (Freight Ops)</p>"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button(
                f"{'✓ Selected' if is_selected else 'Select ' + c_name}",
                key=f"select_btn_{c_id}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state["selected_candidate_key"] = label
                st.rerun()

    selected_dir = candidates[st.session_state["selected_candidate_key"]]
    resume_path = selected_dir / "resume.txt"
    transcript_path = selected_dir / "transcript.txt"
    jd_path = sample_data_dir / "job_description.txt"

    # Missing Document Guard
    if not resume_path.exists() or not transcript_path.exists():
        missing = "resume.txt" if not resume_path.exists() else "transcript.txt"
        st.error(f"❌ Missing required file `{missing}` in `{selected_dir}`.")
        return

    # Expanders: What Happens, Documents, Add Candidate
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        with st.expander("❓ What happens when I click Run? (Pipeline Overview)", expanded=False):
            st.markdown("""
            - 📄 **1. Profile Builder**: Extracts evidence-backed facts & verbatim quotes.
            - 🕵️ **2. Independent Opinions**: 4 isolated agents evaluate via distinct domain lenses.
            - 🗣️ **3. Multi-Round Debate**: Rebuttals challenge peer claims & update scores dynamically.
            - ⚖️ **4. Panel Judge**: Synthesizes evidence-weighted verdict based on lens & confidence.
            - 📊 **5. Report Formatter**: Renders 7-section Markdown report & download artifact.
            """)
    with col_e2:
        with st.expander("📄 View Source Documents & Role JD", expanded=False):
            tab1, tab2, tab3 = st.tabs(["Resume", "Transcript", "Job Description"])
            with tab1:
                st.text_area("Resume Text", load_text_file(resume_path), height=180, disabled=True)
            with tab2:
                st.text_area("Interview Transcript", load_text_file(transcript_path), height=180, disabled=True)
            with tab3:
                st.text_area("Job Description", load_text_file(jd_path), height=180, disabled=True)
    with col_e3:
        with st.expander("➕ Add New Candidate (Upload / Paste)", expanded=False):
            new_cand_name = st.text_input("Candidate Name:", placeholder="e.g. Vikram Sharma", key="new_cand_name")
            folder_id = new_cand_name.lower().replace(" ", "_").strip() if new_cand_name else "new_candidate"

            st.markdown("##### 📄 Resume (`resume.txt`)")
            up_res = st.file_uploader("Upload Resume File (.txt)", type=["txt"], key="up_resume")
            txt_res = st.text_area("Or Paste Resume Text:", height=100, placeholder="Paste resume text...", key="txt_resume")

            st.markdown("##### 🗣️ Interview Transcript (`transcript.txt`)")
            up_trn = st.file_uploader("Upload Transcript File (.txt)", type=["txt"], key="up_transcript")
            txt_trn = st.text_area("Or Paste Interview Transcript:", height=100, placeholder="Paste transcript text...", key="txt_transcript")

            if st.button("💾 Save & Add Candidate", type="primary", use_container_width=True):
                if not new_cand_name.strip():
                    st.error("Please enter a candidate name.")
                else:
                    res_content = up_res.read().decode("utf-8", errors="ignore") if up_res is not None else txt_res.strip()
                    trn_content = up_trn.read().decode("utf-8", errors="ignore") if up_trn is not None else txt_trn.strip()

                    if not res_content or not trn_content:
                        st.error("Both Resume and Interview Transcript are required!")
                    else:
                        new_folder = sample_data_dir / folder_id
                        new_folder.mkdir(parents=True, exist_ok=True)
                        formatted_res = f"{new_cand_name}\n\n{res_content}" if new_cand_name not in res_content[:50] else res_content
                        (new_folder / "resume.txt").write_text(formatted_res, encoding="utf-8")
                        (new_folder / "transcript.txt").write_text(trn_content, encoding="utf-8")

                        new_label = f"{new_cand_name} ({folder_id})"
                        st.session_state["selected_candidate_key"] = new_label
                        st.success(f"✅ Candidate '{new_cand_name}' added to `sample_data/{folder_id}`!")
                        st.rerun()

    # --- RUN BUTTON ---
    st.markdown("<br>", unsafe_allow_html=True)
    run_button = st.button(
        f"🚀 Run Evaluation for {st.session_state['selected_candidate_key'].split(' (')[0]}",
        type="primary",
        use_container_width=True
    )

    # --- PIPELINE EXECUTION ---
    if run_button:
        try:
            config.validate_keys()
        except Exception as e:
            st.error(f"Configuration Error: {e}")
            return

        resume_text = load_text_file(resume_path)
        transcript_text = load_text_file(transcript_path)
        jd_text = load_text_file(jd_path)
        candidate_name = st.session_state['selected_candidate_key'].split(' (')[0]

        status_container = st.container()
        with status_container:
            try:
                st.markdown("### ⚡ Execution Progress Tracker")
                pbar = st.progress(0)

                # Step 1: Profile Builder
                pbar.progress(20)
                render_step_tracker(1, "Extracting evidence-backed Candidate Profile (est. ~10s)...")
                builder = ProfileBuilder(model_name=active_model)
                profile = builder.build(resume_text=resume_text, transcript_text=transcript_text)
                profile.candidate_name = candidate_name
                profile.target_role = "AI Engineer — Agentic Systems (Freight Operations)"
                profile.job_description = jd_text

                # Step 2: 4 Independent Agents
                pbar.progress(40)
                render_step_tracker(2, "Running independent evaluations across 4 panel lenses (est. ~15s)...")
                agents = [
                    TechnicalAgent(model_name=active_model),
                    HRCultureAgent(model_name=active_model),
                    HiringManagerAgent(model_name=active_model),
                    SkepticAgent(model_name=active_model),
                ]
                initial_opinions = [agent.evaluate(profile, job_description_text=jd_text) for agent in agents]

                # Step 3: Debate Orchestrator
                pbar.progress(60)
                render_step_tracker(3, "Conducting multi-round cross-agent debate (est. ~25s)...")
                orchestrator = DebateOrchestrator(agents=agents)
                debate_result = orchestrator.run_debate(profile, initial_opinions=initial_opinions, job_description_text=jd_text)

                # Step 4: Panel Judge
                pbar.progress(80)
                render_step_tracker(4, "Synthesizing consensus verdict via PanelJudge (est. ~10s)...")
                judge = PanelJudge(model_name=active_model)
                final_decision = judge.evaluate_debate(profile, debate_result, job_description_text=jd_text)

                # Step 5: Report Formatter
                pbar.progress(100)
                render_step_tracker(5, "Rendering final report...")
                report_md = ReportFormatter.generate_markdown_report(
                    profile=profile,
                    initial_opinions=initial_opinions,
                    debate_result=debate_result,
                    decision=final_decision
                )

                # Save report
                reports_dir = Path(__file__).parent / "reports"
                reports_dir.mkdir(exist_ok=True)
                report_file = reports_dir / f"{selected_dir.name}_report.md"
                report_file.write_text(report_md, encoding="utf-8")

                st.session_state["active_report_md"] = report_md
                st.session_state["active_decision"] = final_decision
                st.session_state["active_debate"] = debate_result
                st.session_state["active_initial_opinions"] = initial_opinions
                st.session_state["active_profile"] = profile
                st.session_state["active_cand_name"] = candidate_name
                st.session_state["active_cand_dir"] = selected_dir.name

                st.success("✅ Evaluation complete! Results rendered below.")

            except Exception as err:
                logging.exception("Pipeline execution failed:")
                st.error(
                    f"⚠️ **Pipeline Execution Error**: {str(err)}\n\n"
                    "Please check your API key quota, network connection, or candidate document format."
                )
                return

    # --- IDLE WELCOME STATE ---
    if "active_report_md" not in st.session_state:
        st.markdown("---")
        st.markdown(
            """
            <div style='background-color:#F8F9FA; border:1px solid #E0E0E0; border-radius:8px; padding:24px; text-align:center;'>
                <h3 style='color:#1A237E; margin-bottom:8px;'>👋 Welcome to the Autonomous Hiring Panel AI</h3>
                <p style='color:#555; max-width:700px; margin:0 auto 16px auto;'>
                    Select a candidate card above and click <b>🚀 Run Evaluation</b> to execute live multi-agent analysis, 
                    cross-agent debate, and evidence-weighted decision synthesis.
                </p>
                <div style='display:flex; justify-content:center; gap:16px; font-weight:bold; color:#333;'>
                    <span>📄 Fact Extraction</span> ➔ 
                    <span>🕵️ 4 Persona Lenses</span> ➔ 
                    <span>🗣️ Dynamic Debate</span> ➔ 
                    <span>⚖️ Weighted Judge</span> ➔ 
                    <span>📊 Report</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # --- RESTRUCTURED RESULTS DISPLAY (4 CLEAN TABS) ---
    report_md = st.session_state["active_report_md"]
    decision = st.session_state["active_decision"]
    debate_result = st.session_state["active_debate"]
    initial_ops = st.session_state["active_initial_opinions"]
    profile = st.session_state["active_profile"]
    cand_name = st.session_state["active_cand_name"]
    cand_dir_name = st.session_state["active_cand_dir"]

    st.markdown("---")
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.header(f"📊 Evaluation Results: {cand_name}")
    with header_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Download Report (.md)",
            data=report_md,
            file_name=f"{cand_dir_name}_report.md",
            mime="text/markdown",
            use_container_width=True
        )

    # 4 Output Tabs
    tab_summary, tab_opinions, tab_debate, tab_report = st.tabs([
        "🏆 Summary & Verdict",
        "🕵️ Independent Opinions (Before Debate)",
        "🗣️ Multi-Round Debate",
        "📜 Full Report (.md)"
    ])

    # --- TAB 1: SUMMARY & VERDICT ---
    with tab_summary:
        v_color = VERDICT_COLORS.get(decision.final_recommendation, "#1E88E5")
        st.markdown(
            f"""
            <div style='background-color:{v_color}; color:white; padding:20px; border-radius:8px; margin-bottom:20px;'>
                <h2 style='margin:0; color:white;'>Final Verdict: {decision.final_recommendation}</h2>
                <p style='margin:6px 0 0 0; font-size:15px; opacity:0.95;'>
                    <b>Synthesis Mode:</b> Evaluated on agents' <b>FINAL post-debate positions</b> (weighed by PanelJudge), not initial pre-debate scores.
                </p>
                <p style='margin:4px 0 0 0; font-size:14px; opacity:0.9;'>Panel Confidence Level: <b>{decision.confidence_level.upper()}</b></p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### 🧠 Lead Judge Synthesis & Reasoning")
        st.info(decision.key_reasoning)

        scol1, scol2 = st.columns(2)
        with scol1:
            st.markdown("### 🌟 Key Candidate Strengths")
            for s in decision.key_strengths:
                st.markdown(f"- **{s}**")
        with scol2:
            st.markdown("### ⚠️ Unresolved Panel Tensions & Risks")
            for u in decision.unresolved_disagreements:
                st.markdown(f"- 🔴 {u}")

        if decision.risk_mitigations:
            st.markdown("### 🛡️ Required Post-Hire Risk Mitigations")
            for m in decision.risk_mitigations:
                st.markdown(f"- 🔒 {m}")

    # --- TAB 2: AGENT OPINIONS ---
    with tab_opinions:
        st.markdown("### 🕵️ Independent Opinions (Before Debate)")
        st.caption("Initial, isolated verdicts rendered by each agent BEFORE reading peer arguments or entering debate.")
        st.info("💡 **Note**: To see WHY an agent updated their position (e.g. HR moving from LEAN_REJECT ➔ HIRE), check the **🗣️ Multi-Round Debate** tab to read the exact rebuttal exchange.")

        final_opinions = getattr(debate_result, "final_opinions", initial_ops)

        op_cols = st.columns(2)
        for idx, op in enumerate(initial_ops):
            p_cfg = PERSONA_CONFIG.get(op.agent_name, {"color": "#757575", "icon": "👤", "badge": "⚪", "role": op.persona_role})
            op_final = next((o for o in final_opinions if o.agent_name == op.agent_name), op)

            init_rating_str = f"{op.rating} ({op.score}/10)"
            final_rating_str = f"{op_final.rating} ({op_final.score}/10)"

            if op.score != op_final.score or op.rating != op_final.rating:
                position_badge = f"<span style='background-color:#E8F5E9; color:#2E7D32; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px; border:1px solid #C8E6C9;'>Initial: {init_rating_str} ➔ Final: {final_rating_str} (REVISED)</span>"
            else:
                position_badge = f"<span style='background-color:#F5F5F5; color:#555; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px; border:1px solid #E0E0E0;'>Initial: {init_rating_str} ➔ Final: {final_rating_str} (Unchanged)</span>"

            with op_cols[idx % 2]:
                st.markdown(
                    f"""
                    <div style='border-left:6px solid {p_cfg["color"]}; background-color:#FAFAFA; border-top:1px solid #EEE; border-right:1px solid #EEE; border-bottom:1px solid #EEE; padding:14px; border-radius:6px; margin-bottom:16px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <h4 style='margin:0; color:#333;'>{p_cfg["icon"]} {op.agent_name}</h4>
                            {position_badge}
                        </div>
                        <p style='margin:6px 0 8px 0; color:#666; font-size:12px;'><b>Lens:</b> {op.persona_role} | <b>Initial Confidence:</b> {op.confidence}</p>
                        <p style='margin:0; font-size:13.5px; color:#222;'><b>Pre-Debate Rationale:</b> {op.rationale[:200]}...</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                with st.expander(f"Inspect Full {op.agent_name} Initial Rationale & Evidence", expanded=False):
                    st.markdown(f"**Initial Rationale (Pre-Debate):**\n{op.rationale}")
                    if op.concerns:
                        st.markdown("**Identified Concerns / Red Flags:**")
                        for c in op.concerns:
                            st.markdown(f"- 🔴 {c}")
                    if getattr(op, "unresolved_gaps", []):
                        st.markdown("**Unresolved Evidence Gaps:**")
                        for g in op.unresolved_gaps:
                            st.markdown(f"- ⚠️ {g}")
                    st.markdown("**Key Evidence Quotes:**")
                    for ev in op.key_evidence:
                        st.markdown(f"- `[{ev.source_type.upper()}]` *\"{ev.source_quote}\"*")

    # --- TAB 3: DEBATE ---
    with tab_debate:
        dcol1, dcol2 = st.columns([3, 1])
        with dcol1:
            st.markdown("### 🗣️ Phase 2: Cross-Agent Multi-Round Debate")
            st.caption(f"Total Rounds Conducted: {debate_result.total_rounds_conducted} | Rebuttals Generated: {len(debate_result.debate_transcript)}")
        with dcol2:
            st.markdown("<br>", unsafe_allow_html=True)
            voice_btn = st.button("🔊 Generate Voice Debate", use_container_width=True)

        if voice_btn:
            with st.spinner("🎙️ Synthesizing multi-voice audio debate dramatization..."):
                from debate.voice import VoiceDebateGenerator
                audio_file = Path(__file__).parent / "reports" / f"{cand_dir_name}_debate.wav"
                audio_bytes = VoiceDebateGenerator.generate_debate_audio(debate_result, audio_file)

                if audio_bytes:
                    st.session_state[f"audio_bytes_{cand_dir_name}"] = audio_bytes
                    st.success("✅ Voice debate dramatization generated!")
                else:
                    st.warning("⚠️ Voice synthesis is unavailable in this environment.")

        if f"audio_bytes_{cand_dir_name}" in st.session_state:
            st.markdown("#### 🎧 Play Debate Audio Dramatization")
            ab = st.session_state[f"audio_bytes_{cand_dir_name}"]
            acol1, acol2 = st.columns([3, 1])
            with acol1:
                st.audio(ab, format="audio/wav")
            with acol2:
                st.download_button(
                    label="📥 Download Audio (.wav)",
                    data=ab,
                    file_name=f"{cand_dir_name}_debate.wav",
                    mime="audio/wav",
                    use_container_width=True
                )

        # Score Trajectory Table
        st.markdown("#### 📈 Agent Score Trajectory")
        traj_data = []
        for op_init in initial_ops:
            aname = op_init.agent_name
            r1_rebs = [r for r in debate_result.debate_transcript if r.agent_name == aname and r.round_number == 1]
            r2_rebs = [r for r in debate_result.debate_transcript if r.agent_name == aname and r.round_number == 2]

            s_init = op_init.score
            s_r1 = r1_rebs[0].revised_score if (r1_rebs and r1_rebs[0].revised_score is not None) else s_init
            s_r2 = r2_rebs[0].revised_score if (r2_rebs and r2_rebs[0].revised_score is not None) else s_r1
            op_final = next((o for o in debate_result.final_opinions if o.agent_name == aname), op_init)

            delta = s_r2 - s_init
            delta_str = f"+{delta}" if delta > 0 else (str(delta) if delta < 0 else "0 (Unchanged)")

            traj_data.append({
                "Persona Lens": f"{PERSONA_CONFIG.get(aname, {}).get('icon', '')} {aname}",
                "Initial Score": f"{s_init}/10 ({op_init.rating})",
                "Round 1 Score": f"{s_r1}/10",
                "Final Score (Round 2)": f"{s_r2}/10 ({op_final.rating})",
                "Score Shift": delta_str
            })
        st.table(traj_data)

        st.markdown("---")
        st.markdown("#### 💬 Full Debate Transcript")

        for i, reb in enumerate(debate_result.debate_transcript, 1):
            p_cfg = PERSONA_CONFIG.get(reb.agent_name, {"color": "#757575", "icon": "🗣️", "badge": "⚪"})
            stance_icon = "🔴" if reb.stance == "disagree" else ("🟢" if reb.stance == "agree" else "🟡")

            st.markdown(
                f"""
                <div style='border-left:6px solid {p_cfg["color"]}; background-color:#FAFAFA; border:1px solid #EEE; border-left:6px solid {p_cfg["color"]}; padding:14px; border-radius:6px; margin-bottom:14px;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <h4 style='margin:0; color:#1A237E;'>{p_cfg["icon"]} Rebuttal #{i} (Round {reb.round_number}) — <b>{reb.agent_name}</b></h4>
                        <span><b>Stance:</b> {stance_icon} <code>{reb.stance.upper()}</code></span>
                    </div>
                    <p style='margin:4px 0; font-size:13px; color:#555;'><b>Addressing Peer:</b> <code>{reb.target_agent_named}</code></p>
                    <p style='margin:0 0 8px 0; font-size:13px; color:#555;'><b>Point Addressed:</b> <i>"{reb.target_point_referenced}"</i></p>
                    {"<p style='margin:0 0 8px 0; font-size:13px; color:#2E7D32;'><b>Revision:</b> Rating=<code>" + str(reb.revised_rating) + "</code>, Score=<code>" + str(reb.revised_score) + "/10</code></p>" if (reb.revised_rating or reb.revised_score) else ""}
                    <div style='background-color:white; padding:10px; border-radius:4px; border:1px solid #E0E0E0; font-size:13.5px;'>
                        {reb.updated_rationale}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # --- TAB 4: FULL REPORT ---
    with tab_report:
        st.markdown("### 📜 Raw Generated Markdown Report (`report.md`)")
        st.markdown(report_md, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
