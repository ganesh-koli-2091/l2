"""
Tool definitions for the PR Code Review Agent.

Each tool is a pure function decorated with @tool.
Tools return structured strings — they never raise exceptions.
An error result starts with "TOOL_ERROR:" so the agent can detect and retry.
"""

import re
import sys
import os
from pathlib import Path
from langchain_core.tools import tool

# Add parent to path so config is importable when tools.py is run directly
sys.path.insert(0, str(Path(__file__).parent.parent))


def _is_fail_mode() -> bool:
    """Check if deliberate failure injection is enabled."""
    return os.getenv("FAIL_MODE", "false").lower() == "true"


SECURITY_PATTERNS = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']', "Hardcoded password detected"),
    (r'(?i)(api_key|apikey|api_secret)\s*=\s*["\'][^"\']{5,}["\']', "Hardcoded API key detected"),
    (r'(?i)(secret|token)\s*=\s*["\'][^"\']{5,}["\']', "Hardcoded secret/token detected"),
    (r'(?i)(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)[^"\n]*["\'][^"\n]*\+\s*\w', "Potential SQL injection: string concatenation in SQL query"),
    (r'(?i)execute\s*\(\s*[f\'"].*\+', "Potential SQL injection: string passed to execute() with concatenation"),
    (r'(?i)cursor\.execute\s*\(\s*["\'].*%\s*\(', "Potential SQL injection: %-format in query"),
    (r'\beval\s*\(', "Dangerous eval() call"),
    (r'\bexec\s*\(', "Dangerous exec() call"),
    (r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True', "Shell injection risk (shell=True)"),
    (r'pickle\.loads?\s*\(', "Unsafe deserialization: pickle.load"),
    (r'(?i)md5\s*\(|hashlib\.md5', "Weak hashing algorithm: MD5"),
]

QUALITY_PATTERNS = [
    (r'except\s*:\s*\n\s*pass', "Bare except swallowing all errors silently"),
    (r'except\s+Exception\s*:\s*\n\s*pass', "Exception caught and silenced"),
    (r'\bprint\s*\(', "Debug print() statement left in code"),
    (r'#\s*(TODO|FIXME|HACK|XXX)\b', "Unresolved code comment (TODO/FIXME/HACK)"),
]


@tool
def scan_security_issues(code: str) -> str:
    """
    Scans code for security vulnerabilities: hardcoded credentials, SQL injection,
    dangerous function calls (eval/exec), shell injection, unsafe deserialization,
    and weak hashing. ALWAYS call this tool on every code review.
    Returns a plain-text report of findings.
    """
    if _is_fail_mode() or (isinstance(code, str) and code.strip().startswith("INJECT_FAILURE")):
        return "TOOL_ERROR: Security scanner failed — simulated tool failure (FAIL_MODE active)"

    if not code or not isinstance(code, str):
        return "TOOL_ERROR: scan_security_issues received empty or non-string input"

    findings = []
    for pattern, description in SECURITY_PATTERNS:
        matches = re.findall(pattern, code, re.MULTILINE)
        if matches:
            findings.append({
                "severity": "HIGH",
                "description": description,
                "count": len(matches),
            })

    if not findings:
        return "SECURITY_OK: No security vulnerabilities detected."

    lines = [f"SECURITY_FINDINGS — {len(findings)} issue(s) found:"]
    for i, f in enumerate(findings, 1):
        lines.append(f"  {i}. [HIGH] {f['description']} ({f['count']} occurrence(s))")
    return "\n".join(lines)


@tool
def check_code_quality(code: str) -> str:
    """
    Checks code quality: bare except clauses, silenced exceptions, debug print statements,
    unresolved TODOs, overly long functions (>40 lines), and large files (>300 lines).
    ALWAYS call this tool on every code review.
    Returns a plain-text report of findings.
    """
    if not code or not isinstance(code, str):
        return "TOOL_ERROR: check_code_quality received empty or non-string input"

    findings = []

    # Check bare except / silent exceptions
    for pattern, description in QUALITY_PATTERNS:
        if re.search(pattern, code, re.MULTILINE):
            findings.append(f"[MEDIUM] {description}")

    # Check function length
    lines = code.split("\n")
    in_func = False
    func_start = 0
    func_name = ""
    indent_level = 0

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        m = re.match(r"def (\w+)\s*\(", stripped)
        if m:
            if in_func and (i - func_start) > 40:
                findings.append(
                    f"[MEDIUM] Function '{func_name}' is {i - func_start} lines long (keep under 40)"
                )
            in_func = True
            func_start = i
            func_name = m.group(1)
            indent_level = len(line) - len(stripped)

    if in_func and (len(lines) - func_start) > 40:
        findings.append(
            f"[MEDIUM] Function '{func_name}' is {len(lines) - func_start} lines long (keep under 40)"
        )

    # File size check
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if len(code_lines) > 300:
        findings.append(f"[LOW] File has {len(code_lines)} lines of code (consider splitting)")

    if not findings:
        return "QUALITY_OK: No code quality issues detected."

    result_lines = [f"QUALITY_FINDINGS — {len(findings)} issue(s) found:"]
    for i, f in enumerate(findings, 1):
        result_lines.append(f"  {i}. {f}")
    return "\n".join(result_lines)


@tool
def check_api_standards(code: str) -> str:
    """
    Checks REST API route code against conventions: HTTP method correctness,
    explicit status codes, authentication on write endpoints, and lowercase paths.
    Call this tool ONLY when the code contains route decorators such as
    @app.get, @app.post, @router., @api_view, or similar HTTP handler patterns.
    Skip this tool for utility classes, models, or non-route code.
    Returns a plain-text report of findings.
    """
    if not code or not isinstance(code, str):
        return "TOOL_ERROR: check_api_standards received empty or non-string input"

    # Skip if no route definitions found
    has_routes = bool(
        re.search(
            r"@(app|router|blueprint)\.(get|post|put|delete|patch)|"
            r"@api_view\s*\(|"
            r"@require_http_methods",
            code,
            re.IGNORECASE,
        )
    )
    if not has_routes:
        return "API_STANDARDS_SKIP: No API route definitions detected — standards check not applicable."

    findings = []

    # GET used for write operations
    if re.search(r'@\w+\.get\([^)]*\)\s*\ndef\s+(create|add|save|insert|update)', code, re.IGNORECASE):
        findings.append("[HIGH] GET endpoint used for create/write operation — should be POST/PUT")

    # POST used for read operations
    if re.search(r'@\w+\.post\([^)]*\)\s*\ndef\s+(get|fetch|retrieve|list|find)', code, re.IGNORECASE):
        findings.append("[MEDIUM] POST endpoint used for read operation — should be GET")

    # Write endpoints without authentication
    write_endpoints = re.findall(r'@\w+\.(post|put|delete|patch)\s*\(', code, re.IGNORECASE)
    has_auth = bool(re.search(r'(auth|token|bearer|jwt|require_auth|login_required|depend)', code, re.IGNORECASE))
    if write_endpoints and not has_auth:
        findings.append(
            f"[HIGH] {len(write_endpoints)} write endpoint(s) detected without visible authentication"
        )

    # Uppercase path segments
    paths = re.findall(r'@\w+\.\w+\(\s*["\']([^"\']+)["\']', code)
    for path in paths:
        if any(c.isupper() for c in path):
            findings.append(f"[LOW] Path '{path}' uses uppercase — REST convention is lowercase with hyphens")

    # Return without status code
    if re.search(r'return\s+\{.*\}', code) and not re.search(
        r'status_code\s*=|HTTPStatus\.|http\.HTTPStatus|jsonify.*\d{3}', code
    ):
        findings.append("[LOW] Response returned without explicit HTTP status code")

    if not findings:
        return "API_STANDARDS_OK: API endpoints follow REST conventions."

    result_lines = [f"API_STANDARDS_FINDINGS — {len(findings)} issue(s) found:"]
    for i, f in enumerate(findings, 1):
        result_lines.append(f"  {i}. {f}")
    return "\n".join(result_lines)
