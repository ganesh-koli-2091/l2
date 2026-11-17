# PR Code Review Agent — Project Context

## Project Purpose
An agentic code reviewer for backend PRs. The agent uses LangGraph to orchestrate
three analysis tools, requires human approval before finalising, and escalates
when tools fail repeatedly.

## Key Files
- `src/agent.py` — LangGraph StateGraph, nodes, routing, interrupt
- `src/tools.py` — Three @tool functions: security, quality, API standards
- `src/app.py` — Streamlit UI
- `src/cli.py` — Console runner with interrupt handling
- `tests/test_agent.py` — pytest-asyncio test suite

## Architecture
```
START → analyze (LLM + tools) → ToolNode → track_errors → analyze (loop)
      ↓ (no more tools)                   ↓ (3 errors)
   synthesize → [INTERRUPT] → human_gate → generate_report → END
                                          → handle_error → generate_report
```

## Rules
1. Never hardcode the PORTKEY_API_KEY — read from .env
2. Tools must return error strings (TOOL_ERROR: prefix) rather than raise exceptions
3. The human gate MUST run before `generate_report` — do not bypass it
4. Test files mock the LLM; tools use real logic (they are deterministic)
