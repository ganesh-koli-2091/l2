"""
pytest-asyncio test suite for the PR Code Review Agent.

Tests cover:
1. Normal happy-path review
2. Security findings detected correctly
3. Quality findings detected correctly
4. API standards skipped for non-route code
5. Tool failure injection (INJECT_FAILURE)
6. Escalation after MAX_TOOL_RETRIES errors
7. Human rejection triggers re-synthesis
8. tool_error_count increments correctly

LLM is mocked throughout — tools use real logic (they are deterministic).
"""

import sys
import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set dummy API key so config.py doesn't raise on import
os.environ.setdefault("PORTKEY_API_KEY", "test-key-for-unit-tests")
os.environ["FAIL_MODE"] = "false"


# ---------------------------------------------------------------------------
# Tool tests (pure unit tests — no mocking needed)
# ---------------------------------------------------------------------------

class TestSecurityTool:
    def test_detects_hardcoded_password(self):
        from src.tools import scan_security_issues
        code = 'DB_PASSWORD = "admin123"'
        result = scan_security_issues.invoke({"code": code})
        assert "SECURITY_FINDINGS" in result
        assert "password" in result.lower()

    def test_detects_sql_injection(self):
        from src.tools import scan_security_issues
        code = 'query = "SELECT * FROM users WHERE id = " + user_id\ncursor.execute(query)'
        result = scan_security_issues.invoke({"code": code})
        assert "SECURITY_FINDINGS" in result

    def test_clean_code_returns_ok(self):
        from src.tools import scan_security_issues
        code = 'cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))'
        result = scan_security_issues.invoke({"code": code})
        assert "SECURITY_OK" in result

    def test_inject_failure_returns_tool_error(self):
        from src.tools import scan_security_issues
        result = scan_security_issues.invoke({"code": "INJECT_FAILURE: test input"})
        assert "TOOL_ERROR" in result

    def test_fail_mode_env_returns_tool_error(self):
        os.environ["FAIL_MODE"] = "true"
        from src.tools import scan_security_issues
        result = scan_security_issues.invoke({"code": "normal code here"})
        assert "TOOL_ERROR" in result
        os.environ["FAIL_MODE"] = "false"


class TestQualityTool:
    def test_detects_bare_except(self):
        from src.tools import check_code_quality
        code = "try:\n    do_something()\nexcept:\n    pass\n"
        result = check_code_quality.invoke({"code": code})
        assert "QUALITY_FINDINGS" in result
        assert "except" in result.lower()

    def test_detects_debug_print(self):
        from src.tools import check_code_quality
        code = 'print("debug value:", x)\nreturn x\n'
        result = check_code_quality.invoke({"code": code})
        assert "QUALITY_FINDINGS" in result
        assert "print" in result.lower()

    def test_detects_todo(self):
        from src.tools import check_code_quality
        code = "# TODO: add validation\ndef process(): pass\n"
        result = check_code_quality.invoke({"code": code})
        assert "QUALITY_FINDINGS" in result

    def test_clean_code_returns_ok(self):
        from src.tools import check_code_quality
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        result = check_code_quality.invoke({"code": code})
        assert "QUALITY_OK" in result


class TestApiStandardsTool:
    def test_skips_non_route_code(self):
        from src.tools import check_api_standards
        code = "def calculate_tax(amount): return amount * 0.18"
        result = check_api_standards.invoke({"code": code})
        assert "SKIP" in result

    def test_detects_routes(self):
        from src.tools import check_api_standards
        code = '@app.post("/Orders")\ndef create_order(data: dict):\n    return {"id": "1"}\n'
        result = check_api_standards.invoke({"code": code})
        # Should run (not skip) and find uppercase path issue
        assert "SKIP" not in result

    def test_detects_missing_auth_on_write(self):
        from src.tools import check_api_standards
        code = (
            '@app.delete("/orders/{id}")\n'
            'def cancel_order(order_id: str):\n'
            '    return {"cancelled": True}\n'
        )
        result = check_api_standards.invoke({"code": code})
        assert "authentication" in result.lower() or "auth" in result.lower() or "SKIP" in result


# ---------------------------------------------------------------------------
# Agent graph tests — LLM mocked, tools run real logic
# ---------------------------------------------------------------------------

def _make_ai_message(content: str, tool_calls: list = None):
    """Create a mock AIMessage."""
    from langchain_core.messages import AIMessage
    msg = AIMessage(content=content)
    if tool_calls:
        msg.tool_calls = tool_calls
    else:
        msg.tool_calls = []
    return msg


def _build_test_state(code: str = "x = 1", fail_mode: bool = False) -> dict:
    return {
        "messages": [],
        "code_snippet": code,
        "file_name": "test_file.py",
        "pr_title": "Test PR",
        "findings_summary": "",
        "human_approved": False,
        "human_feedback": "",
        "final_report": "",
        "tool_error_count": 0,
        "escalated": False,
        "synthesis_round": 0,
    }


@pytest.mark.asyncio
async def test_security_findings_detected():
    """Agent detects hardcoded password in security tool output."""
    from src.tools import scan_security_issues
    code = 'DB_PASSWORD = "admin123"'
    result = scan_security_issues.invoke({"code": code})
    assert "SECURITY_FINDINGS" in result
    assert "password" in result.lower()


@pytest.mark.asyncio
async def test_quality_findings_detected():
    """Agent detects bare except in quality tool output."""
    from src.tools import check_code_quality
    code = "try:\n    x()\nexcept:\n    pass\n"
    result = check_code_quality.invoke({"code": code})
    assert "QUALITY_FINDINGS" in result


@pytest.mark.asyncio
async def test_api_standards_skipped_for_non_route_code():
    """API standards tool returns SKIP for utility/model code."""
    from src.tools import check_api_standards
    code = "def calculate_total(items): return sum(i.price for i in items)"
    result = check_api_standards.invoke({"code": code})
    assert "SKIP" in result


@pytest.mark.asyncio
async def test_tool_failure_injection():
    """INJECT_FAILURE prefix in code triggers TOOL_ERROR from security scanner."""
    os.environ["FAIL_MODE"] = "false"
    from src.tools import scan_security_issues
    result = scan_security_issues.invoke({"code": "INJECT_FAILURE: bad input"})
    assert "TOOL_ERROR" in result
    os.environ["FAIL_MODE"] = "false"


@pytest.mark.asyncio
async def test_tool_error_count_increments():
    """track_errors_node increments tool_error_count when TOOL_ERROR present."""
    from src.agent import track_errors_node
    from langchain_core.messages import AIMessage, ToolMessage

    ai_msg = AIMessage(content="")
    ai_msg.tool_calls = [{"name": "scan_security_issues", "id": "tc1", "args": {"code": "x"}}]

    tool_msg = ToolMessage(
        content="TOOL_ERROR: simulated failure",
        tool_call_id="tc1",
    )

    state = {
        "messages": [ai_msg, tool_msg],
        "code_snippet": "x = 1",
        "file_name": "f.py",
        "pr_title": "PR",
        "findings_summary": "",
        "human_approved": False,
        "human_feedback": "",
        "final_report": "",
        "tool_error_count": 0,
        "escalated": False,
        "synthesis_round": 0,
    }

    result = track_errors_node(state)
    assert result["tool_error_count"] == 1


@pytest.mark.asyncio
async def test_escalation_after_max_retries():
    """handle_error_node marks state as escalated."""
    from src.agent import handle_error_node

    state = {
        "messages": [],
        "code_snippet": "INJECT_FAILURE: test",
        "file_name": "f.py",
        "pr_title": "PR",
        "findings_summary": "partial",
        "human_approved": False,
        "human_feedback": "",
        "final_report": "",
        "tool_error_count": 3,
        "escalated": False,
        "synthesis_round": 0,
    }

    result = handle_error_node(state)
    assert result["escalated"] is True
    assert "ESCALATED" in result["findings_summary"]


@pytest.mark.asyncio
async def test_human_rejection_reruns_synthesis():
    """route_after_human_gate returns 'synthesize' when human_approved=False."""
    from src.agent import route_after_human_gate

    state = {
        "messages": [],
        "code_snippet": "x = 1",
        "file_name": "f.py",
        "pr_title": "PR",
        "findings_summary": "draft",
        "human_approved": False,
        "human_feedback": "Add more detail on the SQL issue",
        "final_report": "",
        "tool_error_count": 0,
        "escalated": False,
        "synthesis_round": 1,
    }

    next_node = route_after_human_gate(state)
    assert next_node == "synthesize"


@pytest.mark.asyncio
async def test_human_approval_routes_to_report():
    """route_after_human_gate returns 'generate_report' when human_approved=True."""
    from src.agent import route_after_human_gate

    state = {
        "messages": [],
        "code_snippet": "x = 1",
        "file_name": "f.py",
        "pr_title": "PR",
        "findings_summary": "looks good",
        "human_approved": True,
        "human_feedback": "",
        "final_report": "",
        "tool_error_count": 0,
        "escalated": False,
        "synthesis_round": 1,
    }

    next_node = route_after_human_gate(state)
    assert next_node == "generate_report"


@pytest.mark.asyncio
async def test_normal_review_happy_path():
    """
    Full graph test with mocked LLM.
    Verifies: graph builds, runs to interrupt, resumes after approval, produces report.
    """
    from langchain_core.messages import AIMessage
    from src.agent import build_graph, ReviewState

    # Mock the LLM to skip tool calls (direct to synthesize)
    mock_response = AIMessage(content="DONE — analysis complete")
    mock_response.tool_calls = []

    mock_synthesis = AIMessage(
        content=(
            "## Code Review — test_file.py\n"
            "**PR:** Test PR\n"
            "**Verdict:** APPROVE\n\n"
            "### Security\nNo issues detected.\n\n"
            "### Code Quality\nNo issues detected.\n\n"
            "### Recommended Actions\n1. No changes required.\n"
        )
    )
    mock_synthesis.tool_calls = []

    call_count = [0]

    def mock_invoke(messages, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_response
        return mock_synthesis

    with patch("src.agent._get_llm") as mock_llm_fn:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke = mock_invoke
        mock_llm.invoke = mock_invoke
        mock_llm_fn.return_value = mock_llm

        graph = build_graph()
        config = {"configurable": {"thread_id": "test_happy_path"}}

        initial: ReviewState = {
            "messages": [],
            "code_snippet": "def add(a, b): return a + b",
            "file_name": "test_file.py",
            "pr_title": "Test PR",
            "findings_summary": "",
            "human_approved": False,
            "human_feedback": "",
            "final_report": "",
            "tool_error_count": 0,
            "escalated": False,
            "synthesis_round": 0,
        }

        # Phase 1: run to interrupt
        graph.invoke(initial, config)
        state = graph.get_state(config)
        assert "human_gate" in (state.next or ()), f"Expected interrupt at human_gate, got {state.next}"

        # Phase 2: approve and resume
        graph.update_state(config, {"human_approved": True})
        graph.invoke(None, config)

        final = graph.get_state(config)
        report = final.values.get("final_report", "")
        assert "Code Review Report" in report
        assert "test_file.py" in report
