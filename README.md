# 🤖 Multi-Agent Hiring Panel AI

An autonomous, multi-agent AI system that evaluates job candidates by extracting evidence-backed facts, conducting independent evaluations across four specialized panel lenses, facilitating a multi-round cross-agent debate, and synthesizing a non-averaged, risk-categorized hiring recommendation.

---

## 🏗️ Architecture Overview

The system processes raw candidate documents (resumes, interview transcripts) and role requirements through a five-stage pipeline. Rather than relying on a single prompt or averaging numerical scores, each agent operates as an isolated entity with a specialized persona lens, forcing explicit debate, non-coerced position revisions, and grounded decision synthesis.

```
+---------------------+     +-------------------------------------------------+
|  Resume &           |     |             4 Independent Agents                |
|  Interview          | --> | - Technical Lead Agent (Architecture/Stack)     |
|  Transcript         |     | - HR & Culture Specialist (Tenure/Candor)       |
+---------------------+     | - Engineering Director (JD Fit/Delivery)        |
           |                | - Risk & Security Skeptic (Governance/Dissent)  |
           v                +-------------------------------------------------+
+---------------------+                             |
| Profile Builder     |                             v
| (Verbatim Quotes)   |                 +-----------------------+
+---------------------+                 | Debate Orchestrator   |
                                        | (Multi-Round Rebuttal)|
                                        +-----------------------+
                                                    |
                                                    v
+---------------------+                 +-----------------------+
| Streamlit UI &      | <-------------- | Panel Judge           |
| Markdown Reports    |                 | (Risk-Weighted CoT)   |
| (Voice Mode Audio)  |                 +-----------------------+
+---------------------+
```

---

## ⚡ Quick Setup

### 1. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
```

> 🔑 **Get a Free API Key**: Obtain a free Google Gemini API key at [aistudio.google.com](https://aistudio.google.com).

---

## 🚀 How to Run

### Option 1: Interactive Web UI (Streamlit)
Launch the Streamlit web application:
```bash
py -m streamlit run app.py
```
*Open `http://localhost:8501` in your browser to select candidate cards, track live step progress, inspect initial vs. final agent positions, listen to voice debate dramatizations, and download Markdown reports.*

### Option 2: Command Line Interface (CLI)
Run the full pipeline on any candidate directory inside `sample_data/`:
```bash
py main.py sample_data/candidate_a
```
*(Outputs evaluation logs to terminal and saves the final Markdown report to `reports/candidate_a_report.md`)*

### Option 3: Batch Report Generator
Batch-evaluate all candidate folders in `sample_data/`:
```bash
py generate_all_reports.py
```

---

## 📂 Project Structure

```
├── profile_builder/  # Extracts evidence-backed facts paired with verbatim quotes & unverifiable claims.
├── agents/           # 4 isolated persona agents (Technical, HR, Hiring Manager, Skeptic).
├── debate/           # Multi-round debate orchestrator & pyttsx3 voice mode dramatization generator.
│   ├── orchestrator.py  # Cross-agent rebuttal & score revision engine.
│   └── voice.py         # Multi-voice TTS debate audio generator.
├── decision/         # Panel Judge module rendering weighted, risk-categorized final decisions.
├── report/           # Renders 7-section structured Markdown reports and JSON artifacts.
├── sample_data/      # Candidate datasets (candidate_a, candidate_b) and job description.
├── reports/          # Output directory for generated Markdown reports and audio files.
├── app.py            # Streamlit web application interface with 4 output tabs.
├── main.py           # CLI entry point and pipeline orchestrator.
└── config.py         # Centralized system settings and environment key loader.
```

---

## 💡 Key Design Decisions

1. **Isolated LLM Calls Per Agent (No Single-Prompt Multi-Role Playing)**:
   - *Why*: Executing each persona in a dedicated LLM context prevents prompt contamination, persona bleeding, and false consensus. Each agent maintains a strict, un-compromised evaluation lens.
2. **Unverifiable Claim Fact Category & Unresolved Gaps Isolation**:
   - *Why*: Vague candidate assertions lacking concrete numbers (e.g. override rate without metrics) are extracted into an `unverifiable_claim` category. Agents isolate these into `unresolved_gaps` to lower confidence on specific points rather than imposing an automatic overall score penalty.
3. **Revision-Triggered Multi-Round Debate & Anti-Consensus Rules**:
   - *Why*: Round 2 debate fires dynamically only if an agent updates its position in Round 1. Prompts strictly forbid citing meta-consensus ("peers agree") as justification, forcing agents to ground rebuttals in specific facts or peer arguments.
4. **Risk-Categorized Judge Synthesis (No Score Averaging or Vote Counting)**:
   - *Why*: Mathematical score averaging or majority vote counting (e.g., 3-vs-1) erases critical risk signals. The Panel Judge explicitly categorizes dissenting concerns (`integrity/trust risk`, `operational safety risk`, `skill-gap / readiness risk`, `retention / flight risk`) and evaluates whether the risk is mitigable via onboarding or represents a non-negotiable disqualifier.
5. **Offline Multi-Voice Debate Audio Dramatization (`pyttsx3`)**:
   - *Why*: Generates an offline audio dramatization of the multi-round debate using `pyttsx3`, mapping each agent persona to distinct voice properties (pitch, speech rate, male/female voices). Fails gracefully if audio drivers are unavailable.

---

## ⚠️ Known Limitations

- **Free-Tier Rate Limits**: Built for Google Gemini's free tier (`gemini-3.5-flash-lite`), which imposes a limit of 15 requests per minute (RPM). If rate limits occur during heavy debate execution, automatic retry delays handle queueing.
- **Single-Candidate Pipeline Execution**: Processes one candidate folder per execution run.
