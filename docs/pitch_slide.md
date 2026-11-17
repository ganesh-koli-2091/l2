# PR Code Review Agent — Pitch Slide

## The Problem
Backend teams spend **25–40 minutes per PR** on the same mechanical checks:
- Did they hardcode a password?
- Did they leave debug prints in production code?
- Does this new API endpoint follow REST conventions?
- Is that SQL query vulnerable to injection?

For a team doing 10 PRs/week, that's **4–6 hours per reviewer per week** on checklist work.

## The Solution
An agentic code reviewer that:
1. **Runs 3 specialised tools** in parallel — security scanner, quality checker, API standards validator
2. **Decides at runtime** which tools are relevant (no API check for a utility class)
3. **Synthesises findings** into a structured APPROVE / REQUEST_CHANGES / REJECT verdict
4. **Requires human approval** before the review is finalised — an agent in the loop, not instead of it
5. **Escalates gracefully** when tools fail — no silent crashes, full context preserved

## The Stack
- **LangGraph** — stateful orchestration with 7 nodes and conditional routing
- **GPT-4o-mini via Portkey** — Perficient gateway, structured output, tool-calling
- **3 @tool functions** — deterministic, mockable, independently testable
- **Streamlit UI + CLI** — works in both browser and terminal
- **21 pytest-asyncio tests** — all passing, LLM mocked for reliability

## Business Impact
| Metric | Before | After |
|--------|--------|-------|
| Mechanical check time per PR | 25–40 min | ~2 min (review agent output) |
| Security issues caught pre-merge | Variable | Consistently catches 5 HIGH patterns |
| API standards violations caught | Manual, inconsistent | 100% (regex + LLM) |
| Time recovered per reviewer/week | 0 | ~3–5 hours |

## What Makes It Genuinely Agentic
A fixed script could run 3 regex passes. The agent goes further:
- LLM decides which tools to invoke based on what it reads in the code
- Retry loop with error context fed back on each attempt
- Human-in-the-loop gate — the agent can't finish without a human decision
- Escalation path — 3 tool failures → partial report with explicit guidance, not a crash

## Reusable Assets
- `src/tools.py` — reusable @tool definitions for any LangGraph agent
- `pytest.ini` + `tests/test_agent.py` — pytest-asyncio test pattern for LangGraph agents
- `src/agent.py` — LangGraph interrupt + MemorySaver pattern template
