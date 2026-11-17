# Evidence — Run 01: Normal Review (Security Issue Sample)

**Date:** 2026-11-17  
**Input:** `data/samples/sample_security_issue.py`  
**PR Title:** PR #7 — Add order history endpoint  
**Human decision:** Approved

---

## Tool Outputs (captured from Portkey traces)

**scan_security_issues:**
```
SECURITY_FINDINGS — 5 issue(s) found:
  1. [HIGH] Hardcoded password detected (1 occurrence)
  2. [HIGH] Hardcoded API key detected (1 occurrence)
  3. [HIGH] Potential SQL injection: string concatenation in SQL query (1 occurrence)
  4. [HIGH] Shell injection risk (shell=True) (1 occurrence)
  5. [HIGH] Weak hashing algorithm: MD5 (1 occurrence)
```

**check_code_quality:**
```
QUALITY_OK: No code quality issues detected.
```

**check_api_standards:**
```
API_STANDARDS_SKIP: No API route definitions detected — standards check not applicable.
```

---

## Synthesised Review (shown to human at approval gate)

```
## Code Review — sample_security_issue.py
**PR:** PR #7 — Add order history endpoint
**Verdict:** REJECT

### Security
- [HIGH] Hardcoded password detected
- [HIGH] Hardcoded API key detected
- [HIGH] Potential SQL injection: string concatenation in SQL query
- [HIGH] Shell injection risk (shell=True)
- [HIGH] Weak hashing algorithm: MD5

### Code Quality
No issues detected

### API Standards
Not applicable for this file type

### Recommended Actions
1. Remove all hardcoded credentials and replace with environment variable reads
2. Use parameterised queries — no string concatenation in SQL
3. Replace shell=True with argument list in subprocess.run()
4. Replace MD5 with bcrypt/Argon2/PBKDF2 for password hashing
...
```

---

## Human Gate

Human reviewed findings and clicked **Approve** (reviewer accepted the REJECT verdict as correct).

---

## Final Report

Saved to `output/review_sample_security_issue.py_20261117_131620.md`

---

## Observations

- Agent correctly called all 3 tools (security, quality, API standards)
- Agent correctly skipped API standards (no route decorators in file)
- Agent produced REJECT verdict based on 5 HIGH severity findings
- Human gate paused execution at `human_gate` node — confirmed by `state.next == ('human_gate',)`
- Resume via `graph.update_state()` + `graph.invoke(None, config)` worked correctly
