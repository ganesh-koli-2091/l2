"""
Streamlit UI for the PR Code Review Agent.

Run:
    streamlit run src/app.py
"""

import sys
import os
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="PR Code Review Agent",
    page_icon="🔍",
    layout="wide",
)

SAMPLE_FILES = {
    "Sample — Security Issue": "data/samples/sample_security_issue.py",
    "Sample — Quality Issue": "data/samples/sample_quality_issue.py",
    "Sample — API Code": "data/samples/sample_api_code.py",
    "Sample — Clean Code": "data/samples/sample_secure.py",
}


@st.cache_resource(show_spinner=False)
def get_graph():
    from src.agent import build_graph
    return build_graph()


def main():
    st.title("🔍 PR Code Review Agent")
    st.caption(
        "Paste a code snippet → agent runs security, quality, and API standards checks "
        "→ you approve or request changes → final report generated."
    )

    with st.sidebar:
        st.header("Load Sample")
        for label, path in SAMPLE_FILES.items():
            if st.button(label, use_container_width=True):
                full_path = Path(__file__).parent.parent / path
                if full_path.exists():
                    st.session_state["code_input"] = full_path.read_text(encoding="utf-8")
                    st.session_state["file_name"] = Path(path).name

        st.divider()
        st.header("Settings")
        fail_mode = st.checkbox("Inject tool failure (demo)", value=False)
        if fail_mode:
            os.environ["FAIL_MODE"] = "true"
            st.warning("Tool failures will be injected")
        else:
            os.environ["FAIL_MODE"] = "false"

        st.divider()
        st.header("How it works")
        st.markdown(
            "**1. Analyze** — LLM calls security, quality, and API tools\n\n"
            "**2. Synthesise** — LLM writes structured review\n\n"
            "**3. You approve** — Human gate before report is finalised\n\n"
            "**4. Report** — Saved to `output/`\n\n"
            "**On tool failure** — Retries up to 3×, then escalates"
        )

    # Input section
    st.header("1. Provide Code to Review")
    col1, col2 = st.columns(2)
    with col1:
        pr_title = st.text_input("PR Title", value=st.session_state.get("pr_title", "PR #42 — Backend update"))
    with col2:
        file_name = st.text_input("File Name", value=st.session_state.get("file_name", "service.py"))

    code_input = st.text_area(
        "Code snippet",
        value=st.session_state.get("code_input", ""),
        height=300,
        placeholder="Paste your code here, or load a sample from the sidebar…",
    )

    # State management
    if "review_stage" not in st.session_state:
        st.session_state["review_stage"] = "input"
    if "thread_id" not in st.session_state:
        import uuid
        st.session_state["thread_id"] = str(uuid.uuid4())

    # Run analysis
    if st.button("▶ Run Analysis", type="primary", disabled=(not code_input.strip())):
        st.session_state["review_stage"] = "analyzing"
        st.session_state["code_input"] = code_input
        st.session_state["pr_title"] = pr_title
        st.session_state["file_name"] = file_name
        import uuid
        st.session_state["thread_id"] = str(uuid.uuid4())
        st.rerun()

    if st.session_state["review_stage"] == "analyzing":
        graph = get_graph()
        config = {"configurable": {"thread_id": st.session_state["thread_id"]}}

        from src.agent import ReviewState
        initial_state: ReviewState = {
            "messages": [],
            "code_snippet": st.session_state["code_input"],
            "file_name": st.session_state["file_name"],
            "pr_title": st.session_state["pr_title"],
            "findings_summary": "",
            "human_approved": False,
            "human_feedback": "",
            "final_report": "",
            "tool_error_count": 0,
            "escalated": False,
            "synthesis_round": 0,
        }

        with st.spinner("🔍 Analysing code… (30–40 s via Portkey)"):
            graph.invoke(initial_state, config)

        st.session_state["review_stage"] = "awaiting_approval"
        st.session_state["graph_config"] = config
        st.rerun()

    if st.session_state["review_stage"] == "awaiting_approval":
        graph = get_graph()
        config = st.session_state.get("graph_config", {})
        state = graph.get_state(config)

        st.header("2. Review Findings")
        findings = state.values.get("findings_summary", "No findings available.")

        with st.expander("📋 Full findings (click to expand)", expanded=True):
            st.markdown(findings)

        st.header("3. Approve or Request Changes")
        col_approve, col_reject = st.columns(2)

        with col_approve:
            if st.button("✅ Approve", type="primary", use_container_width=True):
                graph.update_state(config, {"human_approved": True, "human_feedback": ""})
                st.session_state["review_stage"] = "generating"
                st.rerun()

        with col_reject:
            feedback = st.text_area("Feedback (required for rejection)", key="rejection_feedback")
            if st.button("❌ Request Changes", use_container_width=True):
                if not feedback.strip():
                    st.error("Please provide feedback before requesting changes.")
                else:
                    graph.update_state(
                        config,
                        {"human_approved": False, "human_feedback": feedback.strip()},
                    )
                    st.session_state["review_stage"] = "re_synthesizing"
                    st.rerun()

    if st.session_state["review_stage"] in ("generating", "re_synthesizing"):
        graph = get_graph()
        config = st.session_state.get("graph_config", {})

        label = "⏳ Revising based on your feedback…" if st.session_state["review_stage"] == "re_synthesizing" else "⏳ Generating final report…"
        with st.spinner(label):
            graph.invoke(None, config)

        # Check if paused again (after re-synthesis)
        state = graph.get_state(config)
        if "human_gate" in (state.next or ()):
            st.session_state["review_stage"] = "awaiting_approval"
        else:
            st.session_state["review_stage"] = "done"
        st.rerun()

    if st.session_state["review_stage"] == "done":
        graph = get_graph()
        config = st.session_state.get("graph_config", {})
        final_state = graph.get_state(config)
        report = final_state.values.get("final_report", "No report generated.")

        st.header("4. Final Report")
        st.success("Review complete — report saved to `output/`")
        st.markdown(report)

        st.download_button(
            "⬇ Download Report",
            data=report,
            file_name=f"review_{st.session_state['file_name']}.md",
            mime="text/markdown",
        )

        if st.button("🔄 Start New Review"):
            st.session_state["review_stage"] = "input"
            st.rerun()


if __name__ == "__main__":
    main()
