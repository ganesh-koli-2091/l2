# PR Code Review Agent — Implementation Plan
**Written: 2026-11-17 | Follows spec.md**

---

## Phase 1 — Project Scaffold (Day 1)
- Create directory structure: `src/`, `data/`, `tests/`, `evidence/`, `docs/`
- Write `requirements.txt` and `.env.example`
- Write `src/config.py` (paths, model name, Portkey URL, constants)
- Write `CLAUDE.md` (agent context document for development)
- Commit as: `chore: project scaffold`

## Phase 2 — Tool Layer (Day 1)
- Write `src/tools.py` with three `@tool`-decorated functions:
  - `scan_security_issues(code)` — regex-based security pattern scan
  - `check_code_quality(code)` — quality checks (bare except, prints, long functions, TODOs)
  - `check_api_standards(code)` — REST conventions (only if routes detected)
- Each tool returns a structured string; never raises — returns `TOOL_ERROR:` prefix on failure
- Write `data/standards/java_rest_standards.md` (reference for API standards tool)
- Write sample code files in `data/samples/`
- Commit as: `feat: add tool layer`

## Phase 3 — LangGraph Agent (Day 2)
- Write `src/agent.py`:
  - `ReviewState` TypedDict with messages, findings_summary, human_approved, tool_error_count, escalated
  - Five nodes: `analyze`, `tools` (ToolNode), `track_errors`, `synthesize`, `human_gate`, `generate_report`, `handle_error`
  - Routing: after `analyze` → tools if tool calls present, else synthesize; after `track_errors` → handle_error if count ≥ 3
  - `interrupt_before=["human_gate"]` with MemorySaver checkpointer
- Commit as: `feat: add langgraph agent`

## Phase 4 — CLI + UI (Day 2)
- Write `src/cli.py` — console runner that handles interrupt, prompts human, resumes graph
- Write `src/app.py` — Streamlit UI with interrupt-aware session state
- Commit as: `feat: add cli and streamlit ui`

## Phase 5 — Tests (Day 3)
- Write `tests/test_agent.py` with pytest-asyncio:
  - `test_normal_review_happy_path`
  - `test_security_findings_detected`
  - `test_quality_findings_detected`
  - `test_api_standards_skipped_for_non_route_code`
  - `test_tool_failure_injection`
  - `test_escalation_after_max_retries`
  - `test_human_rejection_reruns_synthesis`
  - `test_tool_error_count_increments`
- All tests mock the LLM; tools run real logic (deterministic)
- Commit as: `test: add pytest-asyncio suite`

## Phase 6 — Evidence + Docs (Day 3)
- Run agent on sample_security_issue.py, capture output → `evidence/run_01_normal.md`
- Run agent with INJECT_FAILURE input, capture escalation → `evidence/run_02_failure.md`
- Write `docs/failure_analysis.md` (5 failure cases)
- Write `docs/ai_output_review.md` (5-dimension review)
- Write `docs/data_provenance.md`
- Write `docs/improvement_log.md`
- Write `REFLECTION.md`
- Commit as: `docs: add evidence and reflection`

## Phase 7 — Packaging (Day 3)
- Create `Desktop/L2/pr-review-agent.zip`
- Create `docs/capstone_presentation.pptx`
- Create `Desktop/L2/Project_Demo_Guide.md`
