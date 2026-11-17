# Effort Statement

## Time Spent

| Phase | Activity | Time |
|-------|----------|------|
| Design | spec.md, plan.md, tasks.md, architecture decisions | ~2 hrs |
| Tool layer | tools.py — 3 tools with regex patterns, INJECT_FAILURE mode | ~1.5 hrs |
| Agent | agent.py — LangGraph StateGraph, 7 nodes, routing, error handling | ~3 hrs |
| CLI + UI | cli.py, app.py — interrupt handling, Streamlit UI | ~1.5 hrs |
| Tests | test_agent.py — 21 tests, debugging pytest-asyncio config | ~2 hrs |
| Debugging | temperature=0 fix, SQL regex fix, track_errors logic | ~1 hr |
| Evidence | Running agent, capturing output, writing evidence docs | ~1 hr |
| Documentation | failure_analysis.md, ai_output_review.md, reflection.md, etc. | ~1.5 hrs |
| **Total** | | **~13.5 hrs** |

## What Was Cut

1. **Real GitHub PR API integration** — Planned to connect to GitHub REST API to fetch actual PRs. Cut because: requires GitHub token setup, adds network dependency to tests, and the core agent logic is demonstrable with synthetic code snippets.

2. **LangSmith step-level tracing** — Planned for detailed observability. Cut because: requires LangSmith account setup and the Portkey gateway already provides basic LLM-call traces. The LangGraph MemorySaver provides state inspection which serves a similar purpose in the demo.

3. **Java static analysis via PMD/Checkstyle** — Planned to invoke PMD as a tool for real Java analysis. Cut because: requires Java runtime and PMD installation, adding a system dependency. Python code with equivalent patterns achieves the same demonstration.

4. **Persistent ChromaDB storage for review history** — Planned to store previous reviews so the agent could detect "this exact vulnerability was flagged in PR #12 — not fixed". Cut due to complexity and time constraints; in-memory MemorySaver is sufficient for session-scoped memory.

## What Would Be Done Differently

- Start with LangGraph version pinned in requirements.txt to avoid version mismatch surprises
- Write the tool tests before writing the tools (true TDD) — it was faster to test-first for the routing functions
- Use LangSmith from day one for better observability evidence
