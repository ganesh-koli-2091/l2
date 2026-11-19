"""
LangGraph-based PR Code Review Agent.

Graph topology:
    START → analyze → (tool calls?) → tools → track_errors → (errors >= MAX?) → handle_error
                                                                               → analyze (loop)
          → (no tools) → synthesize → [INTERRUPT before human_gate]
                                     → human_gate → (approved?) → generate_report → END
                                                               → (rejected) → synthesize
    handle_error → generate_report → END
"""

import sys
from pathlib import Path
from typing import TypedDict, Annotated, Optional

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import PORTKEY_API_KEY, PORTKEY_BASE_URL, MODEL, MAX_TOOL_RETRIES
from src.tools import scan_security_issues, check_code_quality, check_api_standards
from src.callbacks import tool_tracker
from src.eval import evaluate_faithfulness

TOOLS = [scan_security_issues, check_code_quality, check_api_standards]


class ReviewState(TypedDict):
    messages: Annotated[list, add_messages]
    code_snippet: str
    file_name: str
    pr_title: str
    findings_summary: str
    human_approved: bool
    human_feedback: str
    final_report: str
    tool_error_count: int
    escalated: bool
    synthesis_round: int


ANALYSIS_PROMPT = """You are a senior backend engineer performing a code review.

You have three tools available:
1. scan_security_issues — ALWAYS call this. Checks hardcoded credentials, SQL injection, eval/exec.
2. check_code_quality — ALWAYS call this. Checks bare-except, debug prints, long functions, TODOs.
3. check_api_standards — Call ONLY if the code has HTTP route decorators (@app.get, @router., etc.).

For every review:
- Call scan_security_issues first.
- Call check_code_quality second.
- If you detect route decorators in the code, also call check_api_standards.
- After calling all relevant tools, respond with DONE to signal analysis is complete.

Be concise. Do not repeat findings from previous tool calls."""

SYNTHESIS_PROMPT = """You are writing a formal code review based on tool analysis results.
Format the review exactly as:

## Code Review — {file_name}
**PR:** {pr_title}
**Verdict:** [APPROVE / REQUEST_CHANGES / REJECT]

### Security
[bullet list of security findings, or "No issues detected"]

### Code Quality
[bullet list of quality findings, or "No issues detected"]

### API Standards
[bullet list of API findings, or "Not applicable for this file type"]

### Recommended Actions
[numbered list of specific actions the developer must take before merge]

Base the verdict on:
- APPROVE: no HIGH severity findings
- REQUEST_CHANGES: at least one MEDIUM finding
- REJECT: at least one HIGH severity finding

{feedback_instruction}"""


def _get_llm():
    return ChatOpenAI(
        model=MODEL,
        openai_api_key=PORTKEY_API_KEY,
        openai_api_base=PORTKEY_BASE_URL,
    )


def analyze_node(state: ReviewState) -> dict:
    """LLM decides which tools to call based on the code."""
    llm = _get_llm().bind_tools(TOOLS)

    messages = state.get("messages", [])

    if not messages:
        # First call — build the initial prompt
        messages = [
            SystemMessage(content=ANALYSIS_PROMPT),
            HumanMessage(
                content=(
                    f"Review this code.\n"
                    f"PR: \"{state['pr_title']}\"\n"
                    f"File: {state['file_name']}\n\n"
                    f"```\n{state['code_snippet']}\n```\n\n"
                    f"Use the tools to analyse it, then respond with DONE."
                )
            ),
        ]
    else:
        # Subsequent calls (after tool results returned) — keep message history
        # Prepend system prompt without duplicating
        messages = [SystemMessage(content=ANALYSIS_PROMPT)] + [
            m for m in messages if not isinstance(m, SystemMessage)
        ]

    response = llm.invoke(messages)
    return {"messages": [response]}


def track_errors_node(state: ReviewState) -> dict:
    """After ToolNode executes, count how many tool results contain TOOL_ERROR."""
    messages = state.get("messages", [])
    error_count = state.get("tool_error_count", 0)

    # Scan the most recent tool messages (since last AI message with tool_calls)
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            break  # Stop when we reach the AI message that triggered the tools
        content = str(getattr(msg, "content", ""))
        tool_name = getattr(msg, "name", "tool")
        tool_tracker.record_from_message(tool_name, content)
        if "TOOL_ERROR" in content:
            error_count += 1

    return {"tool_error_count": error_count}


def synthesize_node(state: ReviewState) -> dict:
    """LLM synthesises all tool outputs into a structured review."""
    llm = _get_llm()

    # Collect tool result strings from messages
    tool_results = []
    for msg in state.get("messages", []):
        content = getattr(msg, "content", "")
        if isinstance(content, str) and any(
            prefix in content
            for prefix in ["SECURITY_", "QUALITY_", "API_STANDARDS_", "TOOL_ERROR"]
        ):
            tool_results.append(content)

    feedback_instruction = ""
    if state.get("human_feedback"):
        feedback_instruction = (
            f"\n\nThe human reviewer rejected the previous draft with this feedback:\n"
            f"\"{state['human_feedback']}\"\n"
            f"Incorporate this feedback into the revised review."
        )

    prompt = SYNTHESIS_PROMPT.format(
        file_name=state["file_name"],
        pr_title=state["pr_title"],
        feedback_instruction=feedback_instruction,
    )

    tool_context = "\n\n".join(tool_results) if tool_results else "No tool results available."

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(
            content=f"Tool analysis results:\n\n{tool_context}\n\nWrite the structured code review."
        ),
    ])

    return {
        "messages": [response],
        "findings_summary": response.content,
        "synthesis_round": state.get("synthesis_round", 0) + 1,
    }


def human_gate_node(state: ReviewState) -> dict:
    """
    Placeholder node — the graph is interrupted BEFORE this node.
    The UI/CLI updates human_approved and human_feedback in state,
    then resumes. This node itself does nothing.
    """
    return {}


def generate_report_node(state: ReviewState) -> dict:
    """Formats and saves the final report."""
    from src.config import OUTPUT_DIR
    import datetime

    escalation_note = ""
    if state.get("escalated"):
        escalation_note = (
            "\n\n> ⚠️ **ESCALATED** — Tool failures occurred during analysis. "
            "Manual review required for complete coverage.\n"
        )

    approval_note = ""
    if state.get("human_feedback"):
        approval_note = f"\n\n> **Reviewer note:** {state['human_feedback']}\n"

    # Faithfulness eval — check LLM review reflects actual tool findings
    tool_outputs = [
        str(getattr(msg, "content", ""))
        for msg in state.get("messages", [])
        if any(
            prefix in str(getattr(msg, "content", ""))
            for prefix in ("SECURITY_", "QUALITY_", "API_STANDARDS_", "TOOL_ERROR")
        )
    ]
    faithfulness = evaluate_faithfulness(tool_outputs, state.get("findings_summary", ""))
    faithfulness_note = (
        f"\n\n---\n"
        f"**Eval — Faithfulness score:** {faithfulness.score:.0%}  "
        f"({'✓ verdict consistent' if faithfulness.verdict_consistent else '⚠ verdict may be inconsistent'})"
    )
    if faithfulness.missing:
        faithfulness_note += f"\n*Topics not covered in review: {', '.join(faithfulness.missing[:5])}*"

    # Tool observability summary
    tracker_summary = tool_tracker.summary()
    obs_note = (
        f"\n**Tool calls:** {tracker_summary['total_tool_calls']} total, "
        f"{tracker_summary['successful']} ok, {tracker_summary['failed']} failed"
    )

    report = (
        f"# Code Review Report\n"
        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"**PR:** {state['pr_title']}\n"
        f"**File:** {state['file_name']}\n"
        f"**Status:** {'ESCALATED' if state.get('escalated') else 'REVIEWED — Human approved'}\n"
        f"{escalation_note}"
        f"\n---\n\n"
        f"{state.get('findings_summary', 'No analysis available.')}"
        f"{approval_note}"
        f"{faithfulness_note}"
        f"{obs_note}"
        f"\n\n---\n*Generated by PR Code Review Agent*\n"
    )

    # Save to output/
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = state["file_name"].replace("/", "_").replace("\\", "_")
    out_path = OUTPUT_DIR / f"review_{safe_name}_{ts}.md"
    out_path.write_text(report, encoding="utf-8")

    return {"final_report": report}


def handle_error_node(state: ReviewState) -> dict:
    """Called after MAX_TOOL_RETRIES failures — escalates the review."""
    summary = (
        f"## Code Review — {state['file_name']}\n"
        f"**PR:** {state['pr_title']}\n"
        f"**Verdict:** ESCALATED\n\n"
        f"### Analysis Status\n"
        f"Tool failures occurred {state.get('tool_error_count', 0)} time(s). "
        f"Partial results may be available.\n\n"
        f"### Partial Findings\n"
        f"{state.get('findings_summary', 'No partial findings available.')}\n\n"
        f"### Recommended Actions\n"
        f"1. Trigger manual review — automated analysis could not complete\n"
        f"2. Check PORTKEY_API_KEY and gateway connectivity\n"
        f"3. Re-run with `python src/cli.py` after fixing connectivity\n"
    )
    return {"escalated": True, "findings_summary": summary}


# --- Routing functions ---

def route_after_analyze(state: ReviewState) -> str:
    """After analyze_node: route to tools if LLM made tool calls, else synthesize."""
    messages = state.get("messages", [])
    if not messages:
        return "synthesize"
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        if state.get("tool_error_count", 0) >= MAX_TOOL_RETRIES:
            return "handle_error"
        return "tools"
    return "synthesize"


def route_after_track_errors(state: ReviewState) -> str:
    """After tracking errors: escalate if too many, else loop back to analyze."""
    if state.get("tool_error_count", 0) >= MAX_TOOL_RETRIES:
        return "handle_error"
    return "analyze"


def route_after_human_gate(state: ReviewState) -> str:
    """After human gate: generate report if approved/escalated, else re-synthesize."""
    if state.get("escalated"):
        return "generate_report"
    if state.get("human_approved"):
        return "generate_report"
    # Rejected — re-run synthesis with feedback
    if state.get("synthesis_round", 0) >= 3:
        # Safety valve: after 3 synthesis rounds, force approval
        return "generate_report"
    return "synthesize"


def build_graph():
    """Build and compile the PR Review LangGraph agent."""
    builder = StateGraph(ReviewState)

    builder.add_node("analyze", analyze_node)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_node("track_errors", track_errors_node)
    builder.add_node("synthesize", synthesize_node)
    builder.add_node("human_gate", human_gate_node)
    builder.add_node("generate_report", generate_report_node)
    builder.add_node("handle_error", handle_error_node)

    builder.set_entry_point("analyze")

    builder.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"tools": "tools", "synthesize": "synthesize", "handle_error": "handle_error"},
    )
    builder.add_edge("tools", "track_errors")
    builder.add_conditional_edges(
        "track_errors",
        route_after_track_errors,
        {"analyze": "analyze", "handle_error": "handle_error"},
    )
    builder.add_edge("synthesize", "human_gate")
    builder.add_conditional_edges(
        "human_gate",
        route_after_human_gate,
        {"generate_report": "generate_report", "synthesize": "synthesize"},
    )
    builder.add_edge("generate_report", END)
    builder.add_edge("handle_error", "generate_report")

    checkpointer = MemorySaver()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_gate"],
    )
