"""
CLI runner for the PR Code Review Agent.
Handles the interrupt-based human approval gate interactively.

Usage:
    python src/cli.py
    python src/cli.py --file data/samples/sample_security_issue.py
    python src/cli.py --fail   # inject failure for demonstration
"""

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import build_graph, ReviewState


BANNER = """
╔══════════════════════════════════════════════════════╗
║          PR Code Review Agent  (CLI mode)            ║
╚══════════════════════════════════════════════════════╝
"""


def run_review(code: str, file_name: str, pr_title: str, thread_id: str = "cli_1") -> str:
    """
    Run a code review through the LangGraph agent.
    Handles the human approval interrupt interactively.
    Returns the final report string.
    """
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: ReviewState = {
        "messages": [],
        "code_snippet": code,
        "file_name": file_name,
        "pr_title": pr_title,
        "findings_summary": "",
        "human_approved": False,
        "human_feedback": "",
        "final_report": "",
        "tool_error_count": 0,
        "escalated": False,
        "synthesis_round": 0,
    }

    print("\n🔍 Running analysis… (this may take 30–40 seconds via Portkey)")

    # Phase 1: run until interrupt at human_gate
    graph.invoke(initial_state, config)

    # Check where we stopped
    state = graph.get_state(config)

    if "human_gate" in (state.next or ()):
        # Show findings to human
        findings = state.values.get("findings_summary", "No findings generated.")
        print("\n" + "=" * 60)
        print("📋  REVIEW FINDINGS")
        print("=" * 60)
        print(findings)
        print("=" * 60)

        while True:
            decision = input("\nApprove this review? [y/n]: ").strip().lower()
            if decision in ("y", "n"):
                break
            print("Please enter y or n.")

        feedback = ""
        if decision == "n":
            feedback = input("Feedback for revision (press Enter to skip): ").strip()

        # Update state with human decision and resume
        graph.update_state(
            config,
            {"human_approved": decision == "y", "human_feedback": feedback},
        )
        print("\n⏳ Generating final report…")
        graph.invoke(None, config)

    # Retrieve final report
    final_state = graph.get_state(config)
    report = final_state.values.get("final_report", "No report generated.")

    print("\n" + "=" * 60)
    print("✅  FINAL REVIEW REPORT")
    print("=" * 60)
    print(report)

    return report


def main():
    print(BANNER)
    parser = argparse.ArgumentParser(description="PR Code Review Agent CLI")
    parser.add_argument("--file", type=str, help="Path to code file to review")
    parser.add_argument("--pr", type=str, default="PR #42 — Backend update", help="PR title")
    parser.add_argument("--fail", action="store_true", help="Inject tool failure (demo)")
    args = parser.parse_args()

    if args.fail:
        os.environ["FAIL_MODE"] = "true"
        print("⚠️  FAIL_MODE enabled — tool failures will be injected")

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: file not found: {args.file}")
            sys.exit(1)
        code = file_path.read_text(encoding="utf-8")
        file_name = file_path.name
    else:
        # Interactive input
        print("No file specified. Enter code to review (type END on a new line when done):")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        code = "\n".join(lines)
        file_name = input("File name (e.g. UserService.java): ").strip() or "unknown.py"

    pr_title = args.pr
    run_review(code, file_name, pr_title)


if __name__ == "__main__":
    main()
