# PR Code Review Agent

**L2_Case05_Open_Choice_Agent** — Perficient Global AI-First Academy

A LangGraph-based agentic code reviewer that analyses backend code for security
vulnerabilities, quality issues, and REST API standards violations — with a mandatory
human approval gate before any review is finalised.

---

## Setup (5 minutes)

### Prerequisites
- Python 3.11+
- Portkey API key (Perficient AI Academy — set as `PORTKEY_API_KEY` in `.env`)

### Steps

```bash
# 1. Navigate to the project
cd pr-review-agent

# 2. Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
copy .env.example .env
# Open .env and set: PORTKEY_API_KEY=your_portkey_api_key_here

# 5. Run tests (no API key needed — LLM mocked)
pytest tests/ -v

# 6. Launch CLI
python src/cli.py --file data/samples/sample_security_issue.py

# 7. Launch Streamlit UI
streamlit run src/app.py
```

---

## Demo — Failure Injection

```bash
# Inject deliberate tool failure (shows escalation path)
python src/cli.py --file data/samples/sample_security_issue.py --fail
```

---

## Project Structure

```
pr-review-agent/
├── spec.md                      ← Specification (committed first)
├── plan.md                      ← Phase plan (committed second)
├── tasks.md                     ← Task checklist (committed third)
├── CLAUDE.md                    ← Project context for AI development
├── requirements.txt
├── .env.example
├── pytest.ini
│
├── src/
│   ├── config.py                ← Paths, model, API key, constants
│   ├── tools.py                 ← @tool functions: security, quality, API standards
│   ├── agent.py                 ← LangGraph StateGraph + all nodes + routing
│   ├── cli.py                   ← Console runner with interrupt handling
│   └── app.py                   ← Streamlit UI
│
├── data/
│   ├── standards/
│   │   └── java_rest_standards.md
│   └── samples/
│       ├── sample_secure.py
│       ├── sample_security_issue.py
│       ├── sample_quality_issue.py
│       └── sample_api_code.py
│
├── tests/
│   └── test_agent.py            ← 21 pytest-asyncio tests
│
├── output/                      ← Generated review reports (created at runtime)
│
├── evidence/
│   ├── run_01_normal.md         ← Captured normal run output
│   └── run_02_failure.md        ← Captured failure + escalation output
│
├── REFLECTION.md
│
└── docs/
    ├── data_provenance.md
    ├── failure_analysis.md
    ├── ai_output_review.md
    ├── improvement_log.md
    ├── effort_statement.md
    ├── pitch_slide.md
    └── capstone_presentation.pptx
```

---

## L2 Dimensions Covered

| Dimension | Evidence |
|-----------|----------|
| Spec-Driven Development | spec.md → plan.md → tasks.md committed before any code |
| AI-Powered Development | Claude Code used throughout; tool design AI-assisted |
| Agent Design & Orchestration | LangGraph StateGraph with 7 nodes, conditional routing |
| Agentic Operations | Retry (3×), escalation, observability via Portkey traces |
