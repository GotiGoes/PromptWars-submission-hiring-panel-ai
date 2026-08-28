# 🧑‍💼 Autonomous Multi-Agent Hiring Panel AI

An autonomous, multi-agent AI system that evaluates job candidates by extracting evidence-backed facts, conducting independent evaluations across four specialized panel lenses, facilitating a multi-round cross-agent debate, and synthesizing a non-averaged, risk-categorized hiring recommendation with actionable candidate growth roadmaps.

---

## ✨ Features at a Glance

- 🕵️ **4 Autonomous Agent Lenses**: *Technical Lead*, *HR & Culture Specialist*, *Engineering Director*, and *Risk & Security Skeptic*.
- 🗣️ **Multi-Round Cross-Agent Debate**: Rebuttals challenge peer claims and dynamically update scores across debate rounds.
- ⚖️ **Risk-Categorized Panel Judge**: Synthesizes consensus verdicts by evaluating non-negotiable risk categories (*integrity/trust risk*, *operational safety risk*, *skill-gap risk*) without simple vote counting.
- 🎓 **Actionable Candidate Growth Roadmap**: Generates constructive feedback and skill improvement steps for the interviewed candidate.
- 🎯 **Adjacent Roles Matcher**: Identifies 2–3 alternative career fields and adjacent technical roles where the candidate's skills excel.
- 🎙️ **Offline Multi-Voice Audio Dramatization**: Synthesizes multi-voice audio debate dramatizations locally using `pyttsx3` with zero external API fees.
- 🎨 **Purple & Red High-Contrast UI**: Designed with rich purple/red background containers and bold black text (`#000000`) for maximum legibility.
- 🧪 **1-Click Multi-Layer Integrity Suite**: Automated test suite (`py test_full_integrity_audit.py`) verifying data encoding, Python syntax, fact veracity, and report generation.

---

## 🏆 Quick Start Guide (30-Second Walkthrough for Reviewers)

Follow these 3 simple steps to launch and test the interactive web interface:

### 1. Installation & Key Setup
```bash
# 1. Clone repository & install dependencies
pip install -r requirements.txt

# 2. Create environment configuration file
cp .env.example .env
```
> **API Key Setup**: Add your Gemini API Key in `.env` (`GEMINI_API_KEY=your_key_here`). Get a free key at [aistudio.google.com](https://aistudio.google.com).

### 2. Launch Interactive Web App
```bash
py -m streamlit run app.py
```
> *Open `http://localhost:8501` in your browser.*

### 3. Step-by-Step Evaluation Walkthrough
1. **Select a Candidate**: Click **Rohan Malhotra** (Candidate A) or **Ananya Iyer** (Candidate B) at the top of the page.
2. **Run Evaluation Panel**: Click the primary button **`🚀 Step 2: Run Live Evaluation Panel`**. Watch the 5-stage live pipeline execute.
3. **Explore 4 Interactive Output Tabs**:
   - 🏆 **Summary & Verdict**: Panel Judge CoT reasoning, risk categorization, required onboarding mitigations, **Candidate Growth Roadmap**, and **Adjacent Roles Matcher**.
   - 🕵️ **Independent Opinions**: Pre-debate vs post-debate positions side-by-side.
   - 🗣️ **Multi-Round Debate**: Score trajectory table, color-coded rebuttals, and **Offline Voice Debate Audio Player** (`🔊 Generate Voice Debate`).
   - 📜 **Full Report**: Complete 7-section structured Markdown document with 1-click download (`📥 Download Report`).

---

## ♿ Previous Competition Feedback & Accessibility Enhancements

> **Previous Judging Feedback**: *In an earlier competition submission, the project received a 30% rating on accessibility due to low-contrast grey text, unreadable header elements, and an unclear evaluation workflow.*

This release addresses **100% of the judge feedback** through comprehensive accessibility and usability improvements:

| Judge Feedback Area | Original Issue | Resolution in Current Version |
| :--- | :--- | :--- |
| 🎨 **Typography & Contrast** | Faint grey text over white backgrounds caused low legibility. | Enforced **bold black text (`#000000`)** across all body copy, headings, and tables against rich purple and rose red background containers (`#FAF5FF`, `#F3E8FF`, `#EDE9FE`, `#FFE4E6`). |
| 🏷️ **Color-Only Statuses** | Verdicts relied solely on color badges. | Implemented **Dual-Indicator Status Badges** combining text, icons, and contrast borders (e.g. `[🟢 STRONG HIRE]`, `[✅ HIRE]`, `[⚠️ HOLD]`, `[🚫 NO HIRE]`). |
| 💡 **User Guidance** | Reviewers struggled to understand how to test the app. | Added a prominent **30-Second Quick Start Guide** banner at the top of the Streamlit home screen and `README.md`. |
| 🔘 **Button Readability** | Unselected candidate buttons rendered dark text on dark backgrounds. | Styled secondary unselected buttons with **Soft Lavender Purple (`#EDE9FE`) background and bold black text (`#000000`)** before hover. |
| 🔊 **Auditory Access** | Output was text-only. | Added an **Offline Multi-Voice Audio Generator (`pyttsx3`)** to dramatize the debate transcript for auditory accessibility. |
| 💬 **Screen-Reader Support** | Buttons and controls lacked aria/help descriptions. | Added explicit `help=` tooltips across every button, selectbox, file uploader, and download control. |

---

## 🏗️ System Architecture & Pipeline

```
+-----------------------------------------------------------------------------------+
|                            STAGE 1: PROFILE BUILDER                               |
|   Extracts evidence-backed facts, verbatim quotes, and unverifiable claims        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        STAGE 2: 4 INDEPENDENT PERSONA AGENTS                      |
|  🛠️ Tech Lead  |  👥 HR & Culture  |  👔 Hiring Manager  |  🕵️ Risk Skeptic     |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                      STAGE 3: MULTI-ROUND CROSS-AGENT DEBATE                      |
|  Rebuttals challenge peer claims; Round 2 fires dynamically if scores shift       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                          STAGE 4: RISK-CATEGORIZED JUDGE                          |
|  Synthesizes verdict, candidate growth feedback & adjacent career role matcher    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                     STAGE 5: REPORT FORMATTER & STREAMLIT UI                      |
|  Renders 7-section Markdown report & offline multi-voice audio dramatization      |
+-----------------------------------------------------------------------------------+
```

---

## 🎯 The 4 Autonomous Agent Lenses

| Persona | Lens / Focus | Key Evaluation Criteria |
| :--- | :--- | :--- |
| 🛠️ **Technical Lead Agent** | System Architecture & Delivery | Engineering depth, stack mastery, concurrency, production incident handling. |
| 👥 **HR & Culture Specialist** | People & Organizational Fit | Tenure stability, candor under pressure, self-awareness, retention risk. |
| 👔 **Engineering Director** | Delivery Impact & JD Fit | Role alignment, business execution, team leadership, strategic delivery. |
| 🕵️ **Risk & Security Skeptic** | Governance & Liability | Resume inflation, security boundaries, operational hazards, unmitigated gaps. |

---

## 🧪 Running Automated System Integrity Checks

Run the automated 3-stage integrity audit to verify system data, syntax, and LLM quote veracity:

```bash
py test_full_integrity_audit.py
```

**Audit Checks Performed**:
- ✅ **Audit 1: Sample Data Integrity**: Verifies UTF-8 encoding and file completeness for all candidate resumes, transcripts, and job descriptions.
- ✅ **Audit 2: Codebase Syntax**: Compiles all 34 Python modules cleanly with zero syntax errors.
- ✅ **Audit 3: Fact Grounding Veracity & Pipeline**: Runs the live pipeline to ensure 100% quote grounding (0 ungrounded quotes) and validates all 7 report sections.

---

## 🚀 Execution Modes

### Option 1: Streamlit Web UI (Recommended)
```bash
py -m streamlit run app.py
```

### Option 2: Command Line Interface (CLI)
```bash
py main.py sample_data/candidate_a
```
*(Outputs evaluation logs to terminal and writes `reports/candidate_a_report.md`)*

### Option 3: Batch Report Generator
```bash
py generate_all_reports.py
```

---

## 📂 Project Structure

```
├── profile_builder/           # Fact extraction engine & AI candidate generator.
├── agents/                    # 4 isolated persona agents (Technical, HR, Director, Skeptic).
├── debate/                    # Multi-round debate orchestrator & pyttsx3 voice mode engine.
├── decision/                  # Panel Judge module rendering weighted final decisions & growth plans.
├── report/                    # Renders 7-section structured Markdown reports.
├── sample_data/               # Benchmark candidate datasets (candidate_a, candidate_b) and job description.
├── reports/                   # Output directory for generated Markdown reports and audio files.
├── test_full_integrity_audit.py # Multi-layer integrity audit test suite.
├── app.py                     # Streamlit web application with accessible purple/red UI.
├── main.py                    # CLI entry point and pipeline orchestrator.
├── config.py                  # Centralized system settings and environment key loader.
└── .env.example               # Environment template for reviewer setup.
```
