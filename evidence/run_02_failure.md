# Evidence — Run 02: Deliberate Tool Failure + Escalation

**Date:** 2026-11-17  
**Input:** Code containing `INJECT_FAILURE:` prefix  
**Purpose:** Demonstrate failure handling and escalation path  
**FAIL_MODE:** true (via environment variable)

---

## Failure Injection Method

The `scan_security_issues` tool checks for two failure triggers:
1. `INJECT_FAILURE:` prefix in the code input
2. `FAIL_MODE=true` environment variable

When either is true, the tool returns:
```
TOOL_ERROR: Security scanner failed — simulated tool failure (FAIL_MODE active)
```

This simulates real-world scenarios: network timeout to a scanning service,
malformed tool output, schema mismatch.

---

## Failure Trace

```
Turn 1: analyze_node → LLM calls scan_security_issues
         → tools node executes scan_security_issues
         → ToolMessage: "TOOL_ERROR: Security scanner failed..."
         → track_errors_node: tool_error_count = 1

Turn 2: analyze_node → LLM retries with error context in messages
         → tools node executes scan_security_issues again
         → ToolMessage: "TOOL_ERROR: Security scanner failed..."
         → track_errors_node: tool_error_count = 2

Turn 3: analyze_node → LLM retries again
         → tools node executes scan_security_issues again
         → ToolMessage: "TOOL_ERROR: Security scanner failed..."
         → track_errors_node: tool_error_count = 3

Route: tool_error_count (3) >= MAX_TOOL_RETRIES (3)
       → handle_error_node
       → generate_report_node (escalated=True)
       → END
```

---

## Escalation Report Generated

```markdown
# Code Review Report
PR: PR #42 — Backend update
File: test_failure.py
Status: ESCALATED

## Code Review — test_failure.py
**Verdict:** ESCALATED

### Analysis Status
Tool failures occurred 3 time(s). Partial results may be available.

### Recommended Actions
1. Trigger manual review — automated analysis could not complete
2. Check PORTKEY_API_KEY and gateway connectivity
3. Re-run with python src/cli.py after fixing connectivity
```

---

## Key Observations

- The retry loop fired 3 times before escalation (matches MAX_TOOL_RETRIES=3 in config.py)
- Each retry included the previous TOOL_ERROR in the LLM's context window
- After 3 failures, `handle_error_node` was invoked — not the `human_gate`
- The escalation report explicitly names what failed and what to do next
- **Human gate is bypassed on escalation** — this is intentional since an incomplete review should not go through normal approval

---

## Test Coverage for This Path

`tests/test_agent.py::test_escalation_after_max_retries` — asserts `escalated=True` from `handle_error_node`  
`tests/test_agent.py::test_tool_error_count_increments` — asserts counter increments correctly  
`tests/test_agent.py::test_tool_failure_injection` — asserts INJECT_FAILURE returns TOOL_ERROR
