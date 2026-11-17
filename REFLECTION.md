# Reflection — PR Code Review Agent
**L2_Case05_Open_Choice_Agent | 2026-11-17**

---

## What Was Built

A LangGraph-based code review agent that analyses backend code for security vulnerabilities,
quality issues, and REST API standards violations, with a mandatory human approval gate before
any review is finalised.

The core loop: `analyze (LLM + tools) → ToolNode → track_errors → synthesize → [interrupt] → human_gate → generate_report`.

Three tools:
1. `scan_security_issues` — regex-based detection of hardcoded credentials, SQL injection, eval/exec, shell injection, weak hashing
2. `check_code_quality` — detects bare-except clauses, debug print statements, TODO comments, long functions
3. `check_api_standards` — REST convention checker (HTTP method misuse, missing auth on write endpoints, uppercase paths)

---

## Why an Agent Was Justified

A plain script could run all three tools and print results. It could not:
- Decide at runtime whether `check_api_standards` is relevant (a utility class has no routes — calling the tool wastes tokens and confuses the synthesis)
- Synthesise findings from three different tools into a coherent APPROVE/REJECT verdict using judgement about severity and context
- Require human approval before the review is "posted" (a script either posts or doesn't — it has no interrupt mechanism)
- Adapt its retry strategy based on the specific failure reason returned by a tool

The LangGraph interrupt-before pattern was essential for the human gate. I could not have implemented this cleanly as a script.

---

## What Failed During the Build

**1. temperature=0 crash.** The initial `_get_llm()` passed `temperature=0` to `ChatOpenAI`. Azure OpenAI GPT-4o-mini via Portkey returns a 400 error for this — it only accepts the default temperature. First real end-to-end run crashed immediately. Fix: remove `temperature=0`.

**2. SQL injection regex false negative.** The initial regex only caught injection patterns _inside_ `cursor.execute()`. The more common pattern — building the query string on a previous line, then passing the variable — was missed. The test caught this: `test_detects_sql_injection` failed. Fix: added a broader SQL keyword + concatenation pattern.

**3. pytest-asyncio strict mode.** pytest-asyncio 1.5.0 runs in STRICT mode by default and required either `asyncio_mode = auto` in `pytest.ini` or decorators on every test. The initial run had warnings and inconsistent test collection. Fix: added `pytest.ini` with the right config.

**4. Infinite loop on repeated rejection.** `route_after_human_gate` had no circuit-breaker. If a human rejected 3 times, the graph looped indefinitely between `synthesize` and `human_gate`. Fix: added `synthesis_round` counter; force `generate_report` after 3 rounds.

---

## How I Fixed Them

Each fix was small and local: one-line removal for temperature, two-line regex addition, four-line `pytest.ini`, four-line circuit-breaker. The important thing is that the tests caught failures 2 and 3 immediately — I ran the pytest suite before any real LLM call, and the SQL test failure pointed directly to the regex.

Failure 4 was caught by reviewing the routing logic before submitting rather than finding it at runtime — a benefit of writing the routing tests first.

---

## What I Would Do Differently

1. **Pin LangGraph version in requirements.txt from the start.** The LangGraph 1.x API is slightly different from 0.2.x examples online. Pinning would have avoided early confusion about whether `MemorySaver` or `InMemoryCheckpointer` was the right class name.

2. **Use LangSmith from day one.** The `track_errors_node` was hard to reason about without step-level traces. LangSmith's trace view would have shown exactly which tool messages were being processed at each step.

3. **Write tool tests before writing tools.** I wrote the tools first, then the tests. Two of the tool tests failed on the first run (SQL injection, FAIL_MODE env variable). True TDD — writing the test first — would have surfaced the regex gap before writing the tool.

---

## Business Impact

For a 4-developer backend team doing 10 PRs/week:
- **Before:** ~30 minutes of mechanical check per PR = 5 hours/week/developer on checklist work
- **After:** ~2 minutes to review agent output per PR = ~4.5 hours/week recovered per developer
- **Security:** 5 HIGH-severity patterns caught consistently on every PR, every time — not dependent on reviewer attention or experience level

The agent does not replace the reviewer's judgement on architecture, business logic, or design choices. It removes the mechanical checklist from their cognitive load so they can focus on what actually requires human expertise.

---

## Where I Would Not Yet Trust It

1. **Multi-file changes.** The agent sees one file at a time. A credential in `config.py` passed to a function in `service.py` will not be caught.
2. **Obfuscated credentials.** `"".join(["a","d","m","i","n"])` bypasses all regex patterns.
3. **Language-specific nuance.** The tools are optimised for Python. Java-specific patterns (Hibernate HQL injection, Spring Security misconfigurations) are not covered.
4. **Any finding the LLM synthesises that is not backed by a tool result.** The synthesis prompt can occasionally introduce plausible-sounding findings that no tool produced. Each finding should be traced to a specific tool output before trusting it in production.
