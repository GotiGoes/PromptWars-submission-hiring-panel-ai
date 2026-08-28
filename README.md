# 🤖 Autonomous Multi-Agent Hiring Panel AI

An autonomous, multi-agent AI system that evaluates job candidates by extracting evidence-backed facts, conducting independent evaluations across four specialized panel lenses, facilitating a multi-round cross-agent debate, and synthesizing a non-averaged, risk-categorized hiring recommendation.

---

## 🏆 Competition Reviewer Quick Start (30-Second Guide)

If you are a hackathon judge or reviewer evaluating this project, follow these 3 quick steps to run the interactive web interface:

### 1. Installation & Key Setup
```bash
# Clone repo & install dependencies
pip install -r requirements.txt

# Copy configuration template & add your Google Gemini API Key
cp .env.example .env
```
*Add your Gemini API Key in `.env` (`GEMINI_API_KEY=your_key_here`). Get a free key at [aistudio.google.com](https://aistudio.google.com).*

### 2. Launch Interactive Web App
```bash
py -m streamlit run app.py
```
*Open `http://localhost:8501` in your browser.*

### 3. Interactive Evaluation Walkthrough
1. **Select a Candidate Card**: Click **Rohan Malhotra** (Candidate A) or **Ananya Iyer** (Candidate B) at the top.
2. **Run Evaluation**: Click the prominent blue button **`🚀 Step 2: Run Live Evaluation Panel`**. Watch the 5-stage progress bar execute live Gemini API calls.
3. **Inspect the 4 Output Tabs**:
   - 🏆 **Summary & Verdict**: Lead Judge Chain-of-Thought reasoning, risk categorization, and required post-hire mitigations.
   - 🕵️ **Independent Opinions**: Initial pre-debate agent positions vs final post-debate positions side-by-side.
   - 🗣️ **Multi-Round Debate**: Agent score trajectory table, color-coded rebuttals, and **Voice Debate Audio Generator** (`🔊 Generate Voice Debate`).
   - 📜 **Full Report**: Complete 7-section structured Markdown report with 1-click browser download (`📥 Download Report`).

---

## ♿ Accessibility & Usability Features (WCAG 2.1 AA Compliant)

This application was engineered with a strict focus on accessibility, clarity, and usability:

- 🎨 **High-Contrast Visual Hierarchy (WCAG 2.1 AA)**: All body text (`#0F172A`, `#1E293B`) and headings maintain a >7:1 contrast ratio against light backgrounds (`#FFFFFF`, `#F8FAFC`).
- 🏷️ **Dual Status Indicators**: Never relies on color alone. Every verdict and agent rating pairs high-contrast background badges with explicit text and icons (e.g., `[✅ HIRE]`, `[🚫 NO HIRE]`, `[⚠️ HOLD]`).
- 🔊 **Auditory Voice Mode (`pyttsx3`)**: Converts the debate transcript into a multi-voice audio dramatization for auditory accessibility.
- 💬 **Accessible Control Tooltips**: Every interactive button, selector, and uploader includes explicit `help=` tooltips for screen-reader clarity and hover guidance.
- 📐 **Readable Typography Scale**: Minimum body font size of 15px with 1.6 line-height for effortless legibility across display sizes.
- 🧩 **Progressive Disclosure**: Information is structured into 4 logical tabs, preventing cognitive overload and wall-of-text fatigue.

---

## 🏗️ Architecture & 5-Stage Pipeline

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
|  Rebuttals challenge peer points; Round 2 fires dynamically if scores shift       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                          STAGE 4: RISK-CATEGORIZED JUDGE                          |
|  Synthesizes final verdict by evaluating non-negotiable risk categories           |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                     STAGE 5: REPORT FORMATTER & STREAMLIT UI                      |
|  Renders 7-section structured Markdown report & audio debate dramatization       |
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

## 💡 Key Design Decisions

1. **Isolated LLM Calls Per Agent (No Single-Prompt Persona Bleed)**:
   Executing each agent in a dedicated LLM context prevents prompt contamination and forced false consensus.
2. **Unverifiable Claim Fact Category**:
   Vague candidate assertions lacking concrete numbers are extracted into `unverifiable_claim` and routed to `unresolved_gaps` to lower confidence rather than imposing arbitrary penalties.
3. **Revision-Triggered Multi-Round Debate**:
   Round 2 debate fires dynamically only if an agent updates its position in Round 1. Prompts strictly forbid citing meta-consensus ("peers agree") as justification.
4. **Risk-Categorized Judge Synthesis (No Score Averaging or Vote Counting)**:
   The Panel Judge explicitly categorizes dissenting concerns (`integrity/trust risk`, `operational safety risk`, `skill-gap risk`, `retention risk`) and evaluates whether the risk is mitigable via onboarding or represents a non-negotiable disqualifier.
5. **Offline Voice Mode Dramatization (`pyttsx3`)**:
   Generates a multi-voice audio dramatization of the debate using `pyttsx3`, mapping each agent persona to distinct voice properties.

---

## 🚀 How to Run

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
├── profile_builder/     # Fact extraction engine & AI candidate generator.
├── agents/              # 4 isolated persona agents (Technical, HR, Director, Skeptic).
├── debate/              # Multi-round debate orchestrator & pyttsx3 voice mode engine.
├── decision/            # Panel Judge module rendering weighted final decisions.
├── report/              # Renders 7-section structured Markdown reports.
├── sample_data/         # Candidate datasets (candidate_a, candidate_b) and job description.
├── reports/             # Output directory for generated Markdown reports and audio files.
├── app.py               # Streamlit web application with accessible UI & 4 output tabs.
├── main.py              # CLI entry point and pipeline orchestrator.
├── config.py            # Centralized system settings and environment key loader.
└── .env.example         # Environment template for reviewer setup.
```
