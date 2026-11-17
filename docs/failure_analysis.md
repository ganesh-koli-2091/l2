# Failure Analysis — PR Code Review Agent

Five specific inputs that break the prototype, with root causes and fixes.

---

## Failure 1 — Multi-file PR context

**Input:** "Review this PR which changes `UserService.java`, `UserRepository.java`, and `UserController.java`."

**Expected:** Agent reviews all three files together, understanding cross-file relationships  
**Actual:** Agent can only review one code snippet at a time. It has no visibility into how the files interact.

**Root cause:** The agent's `code_snippet` field holds a single string. There is no mechanism to pass multiple files and correlate findings across them (e.g., a method defined in `UserService.java` might be called unsafely in `UserController.java` — this cross-file vulnerability is invisible to the current implementation).

**Fix needed:** Accept a list of `{file_name, code}` pairs. Run analysis per file, then run a cross-file correlation pass asking "do any of these files create a combined vulnerability?"

---

## Failure 2 — Context window overflow on large files

**Input:** A 1,200-line Java file containing the full implementation of an order processing service.

**Expected:** Full analysis  
**Actual:** The LLM receives the full code in the user message. For very large files, this exceeds the context window and the LLM either truncates the input silently or returns a context-length error.

**Root cause:** No chunking or truncation is applied before passing code to the LLM. The synthesis prompt also includes all tool outputs, which further inflates the message size.

**Fix needed:** Add a `MAX_CODE_LENGTH = 8000` guard in `analyze_node`. For files exceeding this, split by function/class and run analysis per chunk, then merge findings.

---

## Failure 3 — LLM calls wrong tool for inline SQL in ORM code

**Input:** 
```python
users = db.session.execute(text(f"SELECT * FROM users WHERE id={user_id}"))
```

**Expected:** `scan_security_issues` detects SQL injection  
**Actual:** The LLM sometimes decides `check_api_standards` is the most relevant tool for database code and calls it first, missing the security issue.

**Root cause:** The analysis system prompt says "Call scan_security_issues ALWAYS" but the LLM occasionally interprets `db.session.execute` as an API call. The instruction is not strong enough to override the LLM's routing decision.

**Fix needed:** Add explicit routing before the LLM call: always call `scan_security_issues` and `check_code_quality` unconditionally in the `analyze_node` as fixed tool calls, not as LLM decisions. Reserve LLM tool-calling for `check_api_standards` which genuinely requires runtime judgment.

---

## Failure 4 — Human gate loops indefinitely

**Input:** Human rejects the review 3 times with feedback but the synthesis keeps producing the same output.

**Expected:** After 3 rejections, the agent should escalate or force-approve  
**Actual:** Without the `synthesis_round >= 3` safety valve, the graph loops between `synthesize` and `human_gate` indefinitely.

**Root cause:** The original `route_after_human_gate` only checked `human_approved` and `escalated`. It had no circuit-breaker for repeated rejections.

**Fix applied:** Added `synthesis_round` counter. If `synthesis_round >= 3`, force `generate_report` regardless of human decision. This is documented in `agent.py:route_after_human_gate`.

---

## Failure 5 — False negative on obfuscated credentials

**Input:**
```python
_p = "".join(["a","d","m","i","n","1","2","3"])  # builds "admin123"
db.connect(password=_p)
```

**Expected:** Security tool detects obfuscated hardcoded credential  
**Actual:** `SECURITY_OK: No security vulnerabilities detected.`

**Root cause:** The regex patterns in `scan_security_issues` match literal string assignments (`password = "value"`). They do not detect credential construction via string building, list joins, base64 decoding, or other obfuscation techniques.

**Fix needed:** Add a second analysis pass using the LLM itself (not regex) to look for semantic indicators of credential construction. The LLM can recognize `"".join(["a","d","m","i","n"...])` as a suspicious pattern even when regex cannot.
