# Evaluation Methodology

## Overview

Two evaluation and observability mechanisms are built into the agent:
1. **Faithfulness evaluator** (`src/eval.py`) — LLM Eval dimension
2. **Tool observability callback** (`src/callbacks.py`) — AI Tool Integration dimension

---

## 1. Faithfulness Evaluator

### Problem it solves

LLM synthesis can hallucinate: it might claim "SQL injection risk detected" even if
`scan_security_issues` returned `SECURITY_OK`. Or it might APPROVE a review despite
3 HIGH security findings. These are silent failures — the agent appears to work but
produces an incorrect verdict.

### How it works

`evaluate_faithfulness(tool_outputs, review_text)` runs after every `generate_report_node`:

1. Collects raw tool output strings from the graph state (e.g. `"SECURITY_FINDINGS — 3 issue(s)"`)
2. Builds a list of **expected keywords** based on which tools reported findings:
   - SECURITY_FINDINGS → ["security", "credential", "password", "sql inject", ...]
   - QUALITY_FINDINGS → ["quality", "except", "print", "todo", ...]
   - API_STANDARDS_FINDINGS → ["api", "endpoint", "route", "auth", ...]
3. Checks how many expected keywords appear in the review text
4. Returns:
   - `score` (0–1): fraction of expected keywords covered
   - `covered`: keywords present in review (correctly mentioned)
   - `missing`: keywords absent from review (potential gaps)
   - `verdict_consistent`: False if APPROVE issued despite tool findings

### Score interpretation

| Score | Meaning |
|-------|---------|
| 1.0   | All expected topics mentioned — full faithfulness |
| 0.5–0.9 | Partial coverage — some findings may be under-represented |
| < 0.5  | Poor coverage — review likely missed key findings |

### Limitations

- Keyword matching is not semantic. The LLM might say "hardcoded secret" (counted as missing)
  instead of "hardcoded password" (counted as covered). Semantic similarity matching
  (e.g. cosine similarity via embeddings) would improve accuracy.
- Does not detect hallucinated findings (things the LLM added that no tool reported).
  An LLM-as-judge approach would be needed to catch this.

---

## 2. Tool Observability Callback

### Problem it solves

Portkey traces LLM API calls but does not show which tools were invoked within a run,
their inputs, outputs, or whether they errored. Without per-tool tracking, debugging a
failed review requires inspecting raw LangGraph state messages manually.

### How it works

`ToolObservabilityCallback` extends LangChain's `BaseCallbackHandler`:

- **`on_tool_start`** — fires when a tool begins execution (via LangChain callbacks)
- **`on_tool_end`** — fires when a tool returns a result
- **`on_tool_error`** — fires if a tool raises an exception
- **`record_from_message`** — called manually from `track_errors_node` to record
  tool results extracted from LangGraph state ToolMessage objects

A module-level `tool_tracker` instance accumulates calls across the graph run.
`tool_tracker.reset()` is called in `cli.py` and `app.py` before each review.

### Output in final report

The report includes a summary line:
```
Tool calls: 3 total, 3 ok, 0 failed
```

And the faithfulness score:
```
Eval — Faithfulness score: 73%  (✓ verdict consistent)
```

### Production improvement

In production, `tool_tracker.summary()` would be sent to a structured log sink
(e.g. Datadog, CloudWatch) with the PR number and reviewer ID, enabling:
- Alert on sustained tool failure rates
- Track which files/languages trigger the most escalations
- Monitor latency per tool over time
