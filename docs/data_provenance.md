# Data Provenance Note

## What the data is

**4 synthetic Python code files** in `data/samples/`, designed to represent realistic
backend code patterns a Java/Python developer would encounter in a code review:

| File | Purpose | Issues present |
|------|---------|----------------|
| `sample_security_issue.py` | Demonstrates credential leaks, SQL injection, shell injection, weak hashing | 5 HIGH security findings |
| `sample_quality_issue.py` | Demonstrates quality anti-patterns: bare except, debug prints, overly long function, TODOs | 4 MEDIUM/LOW findings |
| `sample_api_code.py` | FastAPI route code with REST convention violations | 2 API standards findings |
| `sample_secure.py` | Well-written code — expected APPROVE verdict | 0 findings |

**1 standards reference document** in `data/standards/java_rest_standards.md`:
- Synthetic document representing REST API conventions
- Used as a reference by `check_api_standards` tool

## Where the data came from

All data was **synthetically created** by the author for this project. No real company
code, no production credentials (all credentials in sample files are fake strings like
`"admin123"` and `"sk-prod-abc123xyz789"`), and no PII.

The patterns are drawn from the author's 4 years of Java backend development experience:
- SQL injection via concatenation is the most common Java ORM misuse pattern
- `shell=True` subprocess calls appear in legacy Java-adjacent Python scripts
- MD5 for password hashing appears frequently in legacy codebases

## What it does and does not represent

**Does represent:**
- Realistic security vulnerability patterns in Python backend code
- Common quality anti-patterns seen in production Java/Python services
- Real FastAPI route code that would trigger API standards checks

**Does not represent:**
- Java source code (agent reviews Python; Java patterns are conceptually similar)
- Full microservice implementations
- Real credentials or any real company's code

## Sensitive data handling

No sensitive data present. All "credentials" in sample files are intentionally fake strings
used to trigger detection patterns. The `.env` file (which contains the real Portkey API key)
is excluded from the data corpus and listed in `.gitignore`.
