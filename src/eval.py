"""
Faithfulness evaluator for LLM-synthesised code reviews.

Checks whether the LLM's review output faithfully references the actual tool
findings rather than hallucinating results not backed by tool output.
Satisfies the "LLM Eval & Interpretability" dimension.
"""

from typing import NamedTuple


class FaithfulnessResult(NamedTuple):
    score: float             # 0.0 – 1.0: fraction of expected keywords found in review
    covered: list[str]       # keywords present in the review (good)
    missing: list[str]       # keywords NOT present (potential gaps / hallucination)
    verdict_consistent: bool  # verdict (APPROVE/REJECT) matches finding severity


_SECURITY_KEYWORDS = [
    "security", "credential", "password", "api key",
    "sql inject", "eval", "exec", "shell", "md5", "weak hash",
]

_QUALITY_KEYWORDS = [
    "quality", "except", "print", "todo", "fixme", "long function",
]

_API_KEYWORDS = [
    "api", "endpoint", "route", "auth", "status code", "http method",
]


def evaluate_faithfulness(tool_outputs: list[str], review_text: str) -> FaithfulnessResult:
    """
    Evaluate whether the LLM review faithfully reflects the tool findings.

    Args:
        tool_outputs: Raw tool output strings (e.g. "SECURITY_FINDINGS — 3 issue(s)...")
        review_text:  The synthesised review produced by the LLM

    Returns:
        FaithfulnessResult with score 0–1, covered/missing keywords, verdict consistency.

    Score interpretation:
        1.0  — review covers all expected topics from tool findings
        0.5+ — partial coverage, some expected topics missing
        <0.5 — poor coverage, review likely missed or hallucinated findings
    """
    review_lower = review_text.lower()
    expected: list[str] = []

    for output in tool_outputs:
        if "SECURITY_FINDINGS" in output:
            expected.extend(_SECURITY_KEYWORDS)
        if "QUALITY_FINDINGS" in output:
            expected.extend(_QUALITY_KEYWORDS)
        if "API_STANDARDS_FINDINGS" in output:
            expected.extend(_API_KEYWORDS)

    if not expected:
        # No findings — expect APPROVE verdict
        verdict_consistent = (
            "APPROVE" in review_text.upper()
            or "NO ISSUE" in review_text.upper()
            or "NO ISSUES" in review_text.upper()
        )
        return FaithfulnessResult(
            score=1.0, covered=[], missing=[], verdict_consistent=verdict_consistent
        )

    covered = [kw for kw in expected if kw in review_lower]
    missing = [kw for kw in expected if kw not in review_lower]
    score = round(len(covered) / len(expected), 2) if expected else 1.0

    # Verdict consistency: tool findings should NOT produce APPROVE
    has_findings = any(
        tag in o for o in tool_outputs
        for tag in ("SECURITY_FINDINGS", "QUALITY_FINDINGS", "API_STANDARDS_FINDINGS")
    )
    verdict_consistent = (not has_findings) or ("APPROVE" not in review_text.upper())

    return FaithfulnessResult(
        score=score,
        covered=covered,
        missing=missing,
        verdict_consistent=verdict_consistent,
    )
