# Improvement Log

## Improvement: Added synthesis_round safety valve

**Problem:** The `route_after_human_gate` function had no circuit-breaker for repeated rejections.
If a human rejected the review 3+ times, the agent looped between `synthesize` and `human_gate`
indefinitely.

**Before:** Route function only checked `human_approved` and `escalated` flags.

**After:** Added `synthesis_round` counter. When `synthesis_round >= 3`, the route function
returns `generate_report` regardless of human decision. The final report notes the forced
completion.

**Measurement:**
- Before: Infinite loop in `test_human_rejection_reruns_synthesis` (would run forever)
- After: Loop terminates at round 3; `test_human_approval_routes_to_report` passes

**Code change:** `src/agent.py:route_after_human_gate` — added 4-line check at the top.

---

## Improvement: SQL injection regex broadened

**Problem:** Initial `scan_security_issues` regex for SQL injection only matched patterns
where the string concatenation happened _inside_ a `cursor.execute()` call. It missed
the more common pattern where the query is built on a previous line and passed as a variable.

**Before:**
```python
(r'(?i)execute\s*\(\s*[f\'"].*\+', "SQL injection in execute()"),
```

**After:**
```python
(r'(?i)(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)[^"\n]*["\'][^"\n]*\+\s*\w', "SQL injection via concatenation"),
(r'(?i)execute\s*\(\s*[f\'"].*\+', "SQL injection in execute()"),
```

**Measurement:**
- Before: `test_detects_sql_injection` — FAILED
- After: `test_detects_sql_injection` — PASSED
- All 21 tests pass

---

## Improvement: Removed temperature=0 from LLM constructor

**Problem:** Azure OpenAI GPT-4o-mini via Portkey rejected `temperature=0` with a 400 error.

**Before:** `ChatOpenAI(..., temperature=0)` — crashed on first real LLM call

**After:** `ChatOpenAI(...)` — uses model default; end-to-end test passes

**Measurement:** `evidence/run_01_normal.md` shows successful run with 5 security findings correctly identified.
