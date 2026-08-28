"""Streamlit Web Interface for Hiring Panel AI Evaluation Pipeline.

Polished visual presentation featuring:
- Elegant, non-clashing muted color palette (WCAG 2.1 AA compliant)
- Persona-themed pastel cards (Sapphire, Mint, Lavender, Rose)
- Accessible tooltips & onboarding quick-start guide
- 5-stage visual progress tracker with harmonious step indicators
- 4 restructured output tabs with rich, non-harsh color hierarchy
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
    page_title="Hiring Panel AI — Multi-Agent Evaluation",
    page_icon="🧑‍💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- HARMONIOUS, NON-CLASHING PERSONA PALETTES ---
PERSONA_CONFIG = {
    "Technical Lead Agent": {
        "color": "#1D4ED8",       # Muted Sapphire Blue
        "bg_color": "#EFF6FF",    # Soft Ice Blue
        "text_color": "#1E40AF",
        "border_color": "#BFDBFE",
        "icon": "🛠️",
        "badge": "🔵",
        "role": "Technical Evaluator",
        "desc": "Evaluates architecture, stack depth, and engineering delivery."
    },
    "HR & Culture Specialist Agent": {
        "color": "#047857",       # Muted Emerald Green
        "bg_color": "#ECFDF5",    # Soft Mint Green
        "text_color": "#065F46",
        "border_color": "#A7F3D0",
        "icon": "👥",
        "badge": "🟢",
        "role": "HR & Culture Evaluator",
        "desc": "Evaluates tenure stability, candor, self-awareness, and retention."
    },
    "Engineering Director Agent": {
        "color": "#6D28D9",       # Muted Deep Violet
        "bg_color": "#F5F3FF",    # Soft Lavender
        "text_color": "#5B21B6",
        "border_color": "#DDD6FE",
        "icon": "👔",
        "badge": "🟣",
        "role": "Hiring Manager",
        "desc": "Balances delivery impact, JD requirement fit, and team leadership."
    },
    "Risk & Security Skeptic Agent": {
        "color": "#B91C1C",       # Muted Warm Rose Red
        "bg_color": "#FEF2F2",    # Soft Muted Rose
        "text_color": "#991B1B",
        "border_color": "#FECACA",
        "icon": "🕵️",
        "badge": "🔴",
        "role": "Devil's Advocate",
        "desc": "Probes resume inflation, operational hazards, and security liabilities."
    },
}

VERDICT_CONFIG = {
    "STRONG_HIRE": {"color": "#065F46", "bg": "#ECFDF5", "border": "#A7F3D0", "label": "🟢 STRONG HIRE", "desc": "Unanimous high-confidence recommendation."},
    "HIRE": {"color": "#047857", "bg": "#ECFDF5", "border": "#A7F3D0", "label": "✅ HIRE", "desc": "Recommended for hire with manageable onboarding risks."},
    "LEAN_HIRE": {"color": "#B45309", "bg": "#FEF3C7", "border": "#FDE68A", "label": "🟧 LEAN HIRE", "desc": "Marginal hire recommendation requiring targeted onboarding mitigations."},
    "HOLD": {"color": "#B45309", "bg": "#FEF3C7", "border": "#FDE68A", "label": "⚠️ HOLD", "desc": "Requires additional reference checks or technical follow-up."},
    "LEAN_REJECT": {"color": "#B91C1C", "bg": "#FEF2F2", "border": "#FECACA", "label": "🔻 LEAN REJECT", "desc": "Significant concerns outweigh candidate strengths."},
    "REJECT": {"color": "#991B1B", "bg": "#FEF2F2", "border": "#FECACA", "label": "❌ REJECT", "desc": "Critical skill-gap or operational risk identified."},
    "NO_HIRE": {"color": "#991B1B", "bg": "#FEF2F2", "border": "#FECACA", "label": "🚫 NO HIRE", "desc": "Authoritative non-hire verdict synthesized by Panel Judge."},
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
    """Render horizontal visual progress step tracker with harmonious colors."""
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
                    f"<div style='background-color:#ECFDF5; border-left:5px solid #059669; border:1px solid #A7F3D0; padding:10px; border-radius:6px; font-size:14.5px; color:#065F46; font-weight:bold;'>"
                    f"✓ {icon} {label}</div>",
                    unsafe_allow_html=True
                )
            elif idx == current_step:
                st.markdown(
                    f"<div style='background-color:#EFF6FF; border-left:5px solid #2563EB; border:1px solid #BFDBFE; padding:10px; border-radius:6px; font-size:14.5px; color:#1E40AF; font-weight:bold;'>"
                    f"⏳ {icon} {label}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='background-color:#F8FAFC; border-left:5px solid #94A3B8; border:1px solid #E2E8F0; padding:10px; border-radius:6px; font-size:14.5px; color:#475569;'>"
                    f"{icon} {label}</div>",
                    unsafe_allow_html=True
                )
    st.markdown(f"<p style='font-size:15px; color:#1E293B; margin-top:8px;'><b>Status:</b> {active_detail}</p>", unsafe_allow_html=True)


def main():
    # --- GLOBAL ELEGANT PASTEL & HIGH-CONTRAST STYLES ---
    st.markdown(
        """
        <style>
        body, .stApp {
            color: #0F172A;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #FAFAFC;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #0F172A !important;
            font-weight: 700 !important;
        }
        p, li, label, div {
            color: #1E293B;
            font-size: 15px;
            line-height: 1.6;
        }
        .stButton>button {
            font-weight: 600 !important;
            border-radius: 6px !important;
            font-size: 15px !important;
            padding: 8px 16px !important;
        }
        .stExpander {
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- SIDEBAR CONFIG & METADATA ---
    st.sidebar.title("🧑‍💼 Hiring Panel AI")
    st.sidebar.markdown("**Autonomous Multi-Agent Evaluation System**")
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ System Configuration")

    provider = config.llm_provider.upper()
    active_model = config.gemini_model if config.llm_provider == "gemini" else config.openai_model
    has_key = bool(config.gemini_api_key or os.getenv("GEMINI_API_KEY") or config.openai_api_key)

    st.sidebar.info(f"**Provider:** `{provider}`\n\n**Active Model:** `{active_model}`")

    if has_key:
        st.sidebar.success("✅ **Live API Key Active**\n\nReal-time multi-agent reasoning & debate enabled.")
    else:
        st.sidebar.warning("⚠️ **Mock Mode Active**\n\nNo API Key detected. Add `GEMINI_API_KEY` to `.env` for live LLM calls.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Panel Lenses (4 Agents)")
    for persona, cfg in PERSONA_CONFIG.items():
        st.sidebar.markdown(
            f"<div style='border-left:5px solid {cfg['color']}; background-color:{cfg['bg_color']}; border:1px solid {cfg['border_color']}; padding:10px; border-radius:6px; margin-bottom:8px;'>"
            f"<b style='color:{cfg['text_color']}; font-size:14px;'>{cfg['icon']} {persona.replace(' Agent', '')}</b><br>"
            f"<small style='color:#334155;'><b>Role:</b> {cfg['role']}</small></div>",
            unsafe_allow_html=True
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("📖 **[Read System Documentation](file:///README.md)**")

    # --- MAIN HEADER & USER GUIDANCE ---
    st.title("🧑‍💼 Autonomous Multi-Agent Hiring Panel AI")
    st.markdown(
        "<p style='font-size:17px; color:#334155; margin-top:-10px;'>"
        "<b>4 Autonomous AI Agents</b> evaluate job candidates through distinct professional lenses, engage in multi-round debate, and synthesize evidence-weighted hiring decisions."
        "</p>",
        unsafe_allow_html=True
    )

    # --- QUICK-START ONBOARDING GUIDE FOR JUDGES/REVIEWERS ---
    with st.expander("💡 **Quick Start Guide: How to Use & Test This App (Click to Expand)**", expanded=True):
        st.markdown(
            """
            <div style='background-color:#EEF2FF; border-left:5px solid #4338CA; border:1px solid #C7D2FE; padding:18px; border-radius:8px;'>
                <h4 style='margin-top:0; color:#312E81;'>🚀 3-Step Quick Evaluation Walkthrough</h4>
                <ol style='margin-bottom:8px; padding-left:20px; color:#1E1B4B;'>
                    <li><b>Step 1: Select a Candidate</b> — Pick a benchmark candidate card below (e.g. <b>Rohan Malhotra</b> or <b>Ananya Iyer</b>), or add/generate your own.</li>
                    <li><b>Step 2: Run Evaluation</b> — Click the primary blue button <b>"🚀 Step 2: Run Live Evaluation Panel"</b>. The 5-stage progress bar will track the live LLM pipeline.</li>
                    <li><b>Step 3: Explore 4 Interactive Output Tabs</b>:
                        <ul>
                            <li><b>🏆 Summary & Verdict</b>: Panel Judge CoT reasoning, risk categorization, and required onboarding mitigations.</li>
                            <li><b>🕵️ Independent Opinions</b>: Initial pre-debate agent positions vs final post-debate positions side-by-side.</li>
                            <li><b>🗣️ Multi-Round Debate</b>: Agent score trajectory table, color-coded rebuttals, and Voice Debate Audio player.</li>
                            <li><b>📜 Full Report (.md)</b>: Complete 7-section structured markdown document with 1-click download.</li>
                        </ul>
                    </li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # --- CANDIDATE SELECTION CARDS ---
    sample_data_dir = Path(__file__).parent / "sample_data"
    candidates = discover_candidates(sample_data_dir)

    if not candidates:
        st.error("No valid candidate directories found in `sample_data/` containing `resume.txt` and `transcript.txt`.")
        return

    st.subheader("📋 Step 1: Candidate Selection")
    st.markdown("Select a candidate profile to run through the 4-agent evaluation panel:")

    # Ensure selected candidate key exists in discovered candidates dict
    if "selected_candidate_key" not in st.session_state or st.session_state["selected_candidate_key"] not in candidates:
        st.session_state["selected_candidate_key"] = list(candidates.keys())[0] if candidates else None

    selected_candidate_key = st.session_state["selected_candidate_key"]

    cand_cols = st.columns(max(len(candidates), 1))
    for idx, (label, folder_path) in enumerate(candidates.items()):
        c_name = label.split(" (")[0]
        c_id = folder_path.name
        is_selected = (label == selected_candidate_key)

        with cand_cols[idx % len(cand_cols)]:
            border_color = "#2563EB" if is_selected else "#CBD5E1"
            bg_color = "#EFF6FF" if is_selected else "#FFFFFF"
            status_badge = "<span style='background-color:#1D4ED8; color:white; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:bold;'>✓ CURRENTLY SELECTED</span>" if is_selected else "<span style='background-color:#F1F5F9; color:#475569; padding:4px 10px; border-radius:6px; font-size:12px; border:1px solid #CBD5E1;'>Click to Select</span>"

            st.markdown(
                f"""
                <div style='border:2px solid {border_color}; background-color:{bg_color}; padding:18px; border-radius:10px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.04);'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <h4 style='margin:0; color:#1E3A8A; font-size:18px;'>👤 {c_name}</h4>
                        {status_badge}
                    </div>
                    <p style='margin:8px 0 4px 0; font-size:13.5px; color:#334155;'><b>Folder:</b> <code>sample_data/{c_id}</code></p>
                    <p style='margin:0; font-size:13.5px; color:#334155;'><b>Target Role:</b> AI Engineer (Freight Ops)</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button(
                f"{'✓ Selected: ' + c_name if is_selected else 'Select ' + c_name}",
                key=f"select_btn_{c_id}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
                help=f"Set {c_name} as the active candidate for panel evaluation."
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

    st.markdown("<br>", unsafe_allow_html=True)

    # Expanders: What Happens, Documents, Add Candidate, AI Generator
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1:
        with st.expander("❓ What happens when I click Run?", expanded=False):
            st.markdown("""
            - 📄 **1. Profile Builder**: Extracts evidence-backed facts & verbatim quotes.
            - 🕵️ **2. Independent Opinions**: 4 isolated agents evaluate via distinct domain lenses.
            - 🗣️ **3. Multi-Round Debate**: Rebuttals challenge peer claims & update scores dynamically.
            - ⚖️ **4. Panel Judge**: Synthesizes evidence-weighted verdict based on lens & confidence.
            - 📊 **5. Report Formatter**: Renders 7-section Markdown report & download artifact.
            """)
    with col_e2:
        with st.expander("📄 View Source Documents", expanded=False):
            tab1, tab2, tab3 = st.tabs(["Resume", "Transcript", "Job Description"])
            with tab1:
                st.text_area("Resume Text", load_text_file(resume_path), height=180, disabled=True)
            with tab2:
                st.text_area("Interview Transcript", load_text_file(transcript_path), height=180, disabled=True)
            with tab3:
                st.text_area("Job Description", load_text_file(jd_path), height=180, disabled=True)
    with col_e3:
        with st.expander("➕ Add Candidate (Upload/Paste)", expanded=False):
            new_cand_name = st.text_input("Candidate Name:", placeholder="e.g. Vikram Sharma", key="new_cand_name")
            folder_id = new_cand_name.lower().replace(" ", "_").strip() if new_cand_name else "new_candidate"

            st.markdown("##### 📄 Resume (`resume.txt`)")
            up_res = st.file_uploader("Upload Resume File (.txt)", type=["txt"], key="up_resume", help="Upload text file containing candidate resume.")
            txt_res = st.text_area("Or Paste Resume Text:", height=100, placeholder="Paste resume text...", key="txt_resume")

            st.markdown("##### 🗣️ Interview Transcript (`transcript.txt`)")
            up_trn = st.file_uploader("Upload Transcript File (.txt)", type=["txt"], key="up_transcript", help="Upload text file containing interview transcript.")
            txt_trn = st.text_area("Or Paste Interview Transcript:", height=100, placeholder="Paste transcript text...", key="txt_transcript")

            if st.button("💾 Save & Add Candidate", type="primary", use_container_width=True, help="Save files and add candidate to selection list."):
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

                        fresh_candidates = discover_candidates(sample_data_dir)
                        matched_key = next((k for k, p in fresh_candidates.items() if p.name == folder_id), list(fresh_candidates.keys())[0])
                        st.session_state["selected_candidate_key"] = matched_key
                        st.success(f"✅ Candidate '{new_cand_name}' added to `sample_data/{folder_id}`!")
                        st.rerun()
    with col_e4:
        with st.expander("🪄 AI Generate Candidate (Gemini)", expanded=False):
            archetype_choice = st.selectbox(
                "Archetype Preset:",
                options=[
                    "Senior AI Engineer with high skill but unverified metrics",
                    "Mid-level RAG engineer with prompt security incident history",
                    "Junior developer with rapid job-hopping & high confidence",
                    "Principal architect with strong governance & conservative posture",
                    "Custom Prompt..."
                ],
                key="arch_select",
                help="Choose a pre-defined candidate scenario or provide custom prompt."
            )
            if archetype_choice == "Custom Prompt...":
                user_archetype = st.text_area("Custom Archetype Prompt:", placeholder="e.g. 5 yrs exp, overstates team leadership...", key="custom_arch")
            else:
                user_archetype = archetype_choice

            if st.button("✨ Generate via Gemini", type="primary", use_container_width=True, help="Trigger Gemini API to generate synthetic candidate profile."):
                if not user_archetype.strip():
                    st.error("Please select or enter an archetype prompt.")
                else:
                    with st.spinner("🤖 Generating synthetic resume & interview transcript via Gemini API..."):
                        try:
                            from profile_builder.generator import CandidateGenerator
                            gen = CandidateGenerator(model_name=active_model)
                            gen_name, gen_res, gen_trn = gen.generate_candidate(user_archetype)

                            gen_folder_id = gen_name.lower().replace(" ", "_").strip()
                            gen_folder = sample_data_dir / gen_folder_id
                            gen_folder.mkdir(parents=True, exist_ok=True)

                            (gen_folder / "resume.txt").write_text(gen_res, encoding="utf-8")
                            (gen_folder / "transcript.txt").write_text(gen_trn, encoding="utf-8")

                            fresh_candidates = discover_candidates(sample_data_dir)
                            matched_key = next((k for k, p in fresh_candidates.items() if p.name == gen_folder_id), list(fresh_candidates.keys())[0])
                            st.session_state["selected_candidate_key"] = matched_key
                            st.success(f"✅ Generated candidate '{gen_name}' in `sample_data/{gen_folder_id}`!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to generate candidate: {e}")

    # --- RUN BUTTON ---
    st.markdown("<br>", unsafe_allow_html=True)
    active_cand_display = st.session_state['selected_candidate_key'].split(' (')[0]
    run_button = st.button(
        f"🚀 Step 2: Run Live Evaluation Panel for '{active_cand_display}'",
        type="primary",
        use_container_width=True,
        help=f"Trigger full 5-stage evaluation pipeline for candidate '{active_cand_display}'."
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
        candidate_name = active_cand_display

        status_container = st.container()
        with status_container:
            try:
                st.markdown("### ⚡ Live Pipeline Progress Tracker")
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

                st.success("✅ Evaluation complete! Scroll down or click the output tabs below to view results.")

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
            <div style='background-color:#F8FAFC; border:2px solid #E2E8F0; border-radius:10px; padding:28px; text-align:center;'>
                <h3 style='color:#1E3A8A; margin-bottom:10px;'>👋 Welcome to the Autonomous Hiring Panel AI</h3>
                <p style='color:#334155; max-width:760px; margin:0 auto 20px auto; font-size:16px;'>
                    Select a candidate card above and click <b>🚀 Step 2: Run Live Evaluation Panel</b> to execute live multi-agent analysis, 
                    cross-agent debate, and evidence-weighted decision synthesis.
                </p>
                <div style='display:flex; justify-content:center; gap:20px; font-weight:bold; color:#1E293B; font-size:15px;'>
                    <span>📄 Fact Extraction</span> ➔ 
                    <span>🕵️ 4 Persona Lenses</span> ➔ 
                    <span>🗣️ Dynamic Debate</span> ➔ 
                    <span>⚖️ Weighted Judge</span> ➔ 
                    <span>📊 Structured Report</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # --- RESTRUCTURED RESULTS DISPLAY (4 ACCESSIBLE TABS) ---
    report_md = st.session_state["active_report_md"]
    decision = st.session_state["active_decision"]
    debate_result = st.session_state["active_debate"]
    initial_ops = st.session_state["active_initial_opinions"]
    cand_name = st.session_state["active_cand_name"]
    cand_dir_name = st.session_state["active_cand_dir"]

    st.markdown("---")
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.header(f"📊 Step 3: Evaluation Results for {cand_name}")
    with header_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Download Report (.md)",
            data=report_md,
            file_name=f"{cand_dir_name}_report.md",
            mime="text/markdown",
            use_container_width=True,
            help="Download complete markdown report for offline viewing."
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
        v_cfg = VERDICT_CONFIG.get(decision.final_recommendation, {"color": "#1D4ED8", "bg": "#EFF6FF", "border": "#BFDBFE", "label": decision.final_recommendation, "desc": "Synthesized decision."})
        st.markdown(
            f"""
            <div style='background-color:{v_cfg["bg"]}; border-left:8px solid {v_cfg["color"]}; border:2px solid {v_cfg["border"]}; color:#0F172A; padding:24px; border-radius:10px; margin-bottom:24px;'>
                <h2 style='margin:0; color:{v_cfg["color"]}; font-size:26px;'>Verdict: {v_cfg["label"]}</h2>
                <p style='margin:8px 0 0 0; font-size:16px; color:#1E293B;'>
                    <b>Synthesis Mode:</b> Evaluated on agents' <b>FINAL post-debate positions</b> (weighed by PanelJudge risk categories), not initial pre-debate scores.
                </p>
                <p style='margin:6px 0 0 0; font-size:15px; color:#334155;'>Panel Confidence Level: <b>{decision.confidence_level.upper()}</b> | <i>{v_cfg["desc"]}</i></p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### 🧠 Lead Judge Synthesis & Reasoning")
        st.info(decision.key_reasoning)

        scol1, scol2 = st.columns(2)
        with scol1:
            st.markdown(
                """
                <div style='background-color:#ECFDF5; border:1px solid #A7F3D0; border-left:5px solid #059669; padding:16px; border-radius:8px;'>
                    <h4 style='margin:0 0 8px 0; color:#065F46;'>🌟 Key Candidate Strengths</h4>
                </div>
                """,
                unsafe_allow_html=True
            )
            for s in decision.key_strengths:
                st.markdown(f"- **{s}**")

        with scol2:
            st.markdown(
                """
                <div style='background-color:#FEF2F2; border:1px solid #FECACA; border-left:5px solid #DC2626; padding:16px; border-radius:8px;'>
                    <h4 style='margin:0 0 8px 0; color:#991B1B;'>⚠️ Unresolved Panel Tensions & Risks</h4>
                </div>
                """,
                unsafe_allow_html=True
            )
            for u in decision.unresolved_disagreements:
                st.markdown(f"- 🔴 {u}")

        if decision.risk_mitigations:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style='background-color:#FEF3C7; border:1px solid #FDE68A; border-left:5px solid #D97706; padding:16px; border-radius:8px;'>
                    <h4 style='margin:0 0 8px 0; color:#92400E;'>🛡️ Required Post-Hire Risk Mitigations</h4>
                </div>
                """,
                unsafe_allow_html=True
            )
            for m in decision.risk_mitigations:
                st.markdown(f"- 🔒 {m}")

    # --- TAB 2: AGENT OPINIONS ---
    with tab_opinions:
        st.markdown("### 🕵️ Independent Opinions (Before Debate)")
        st.markdown("<p style='font-size:15px; color:#334155;'>Initial, isolated verdicts rendered by each agent BEFORE reading peer arguments or entering debate.</p>", unsafe_allow_html=True)
        st.info("💡 **Note**: To see WHY an agent updated their position (e.g. HR moving from LEAN_REJECT ➔ HIRE), check the **🗣️ Multi-Round Debate** tab to read the exact rebuttal exchange.")

        final_opinions = getattr(debate_result, "final_opinions", initial_ops)

        op_cols = st.columns(2)
        for idx, op in enumerate(initial_ops):
            p_cfg = PERSONA_CONFIG.get(op.agent_name, {"color": "#475569", "bg_color": "#F8FAFC", "border_color": "#E2E8F0", "text_color": "#0F172A", "icon": "👤", "badge": "⚪", "role": op.persona_role})
            op_final = next((o for o in final_opinions if o.agent_name == op.agent_name), op)

            init_rating_str = f"{op.rating} ({op.score}/10)"
            final_rating_str = f"{op_final.rating} ({op_final.score}/10)"

            if op.score != op_final.score or op.rating != op_final.rating:
                position_badge = f"<span style='background-color:#ECFDF5; color:#065F46; padding:6px 10px; border-radius:6px; font-weight:bold; font-size:13px; border:1px solid #A7F3D0;'>Initial: {init_rating_str} ➔ Final: {final_rating_str} (REVISED)</span>"
            else:
                position_badge = f"<span style='background-color:#F8FAFC; color:#334155; padding:6px 10px; border-radius:6px; font-weight:bold; font-size:13px; border:1px solid #E2E8F0;'>Initial: {init_rating_str} ➔ Final: {final_rating_str} (Unchanged)</span>"

            with op_cols[idx % 2]:
                st.markdown(
                    f"""
                    <div style='border-left:6px solid {p_cfg["color"]}; background-color:{p_cfg["bg_color"]}; border:1px solid {p_cfg["border_color"]}; padding:18px; border-radius:8px; margin-bottom:18px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <h4 style='margin:0; color:{p_cfg["text_color"]}; font-size:18px;'>{p_cfg["icon"]} {op.agent_name}</h4>
                            {position_badge}
                        </div>
                        <p style='margin:6px 0 10px 0; color:#334155; font-size:13.5px;'><b>Lens:</b> {op.persona_role} | <b>Initial Confidence:</b> {op.confidence}</p>
                        <p style='margin:0; font-size:14.5px; color:#0F172A;'><b>Pre-Debate Rationale:</b> {op.rationale[:220]}...</p>
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
            st.markdown(f"<p style='font-size:15px; color:#334155;'>Total Rounds Conducted: <b>{debate_result.total_rounds_conducted}</b> | Rebuttals Generated: <b>{len(debate_result.debate_transcript)}</b></p>", unsafe_allow_html=True)
        with dcol2:
            st.markdown("<br>", unsafe_allow_html=True)
            voice_btn = st.button("🔊 Generate Voice Debate", use_container_width=True, help="Synthesize multi-voice audio dramatization using pyttsx3.")

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
                    use_container_width=True,
                    help="Download debate audio file."
                )

        # Score Trajectory Table
        st.markdown("#### 📈 Agent Score Trajectory Across Debate Rounds")
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
            p_cfg = PERSONA_CONFIG.get(reb.agent_name, {"color": "#475569", "bg_color": "#F8FAFC", "border_color": "#CBD5E1", "text_color": "#0F172A", "icon": "🗣️", "badge": "⚪"})
            stance_icon = "🔴" if reb.stance == "disagree" else ("🟢" if reb.stance == "agree" else "🟡")

            st.markdown(
                f"""
                <div style='border-left:6px solid {p_cfg["color"]}; background-color:{p_cfg["bg_color"]}; border:1px solid {p_cfg["border_color"]}; padding:18px; border-radius:8px; margin-bottom:16px;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <h4 style='margin:0; color:{p_cfg["text_color"]}; font-size:18px;'>{p_cfg["icon"]} Rebuttal #{i} (Round {reb.round_number}) — <b>{reb.agent_name}</b></h4>
                        <span style='font-size:14px;'><b>Stance:</b> {stance_icon} <code>{reb.stance.upper()}</code></span>
                    </div>
                    <p style='margin:6px 0; font-size:14px; color:#334155;'><b>Addressing Peer:</b> <code>{reb.target_agent_named}</code></p>
                    <p style='margin:0 0 10px 0; font-size:14px; color:#334155;'><b>Point Addressed:</b> <i>"{reb.target_point_referenced}"</i></p>
                    {"<p style='margin:0 0 10px 0; font-size:14px; color:#047857;'><b>Position Revision:</b> Rating=<code>" + str(reb.revised_rating) + "</code>, Score=<code>" + str(reb.revised_score) + "/10</code></p>" if (reb.revised_rating or reb.revised_score) else ""}
                    <div style='background-color:#FFFFFF; padding:14px; border-radius:6px; border:1px solid #E2E8F0; font-size:14.5px; color:#0F172A;'>
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
