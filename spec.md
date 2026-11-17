# PR Code Review Agent — Specification
**Written: 2026-11-17 | Status: BASELINE (no code exists yet)**

---

## Problem Statement

A 4-person Java/Python backend team at a fintech firm reviews 8–12 pull requests per week.
Each review involves the same repetitive judgement calls:

- Did the developer introduce a hardcoded credential or SQL injection risk?
- Is the code quality acceptable (no debug prints, no silently-swallowed exceptions)?
- If this code adds an API endpoint, does it follow REST conventions?

Reviewers spend 25–40 minutes per PR on these checks before they even read the business logic.
An agent that handles the mechanical checks and surfaces only genuine issues would recover
~2 hours per reviewer per week.

**Why an agent and not a script?**
A script can run fixed regex patterns. An agent can:
1. Decide at runtime *which* checks are relevant (API standards check is irrelevant for a utility class)
2. Call multiple tools in a single pass and use their combined output to synthesise a judgement
3. Adapt its analysis based on what it finds (if security scan finds a credential leak, deepen that analysis)
4. Require human approval before the review is "posted" (irreversible action)

A three-line script cannot do steps 2–4.

---

## Functional Requirements

| ID   | Requirement |
|------|-------------|
| FR1  | Accept a code snippet, file name, and PR title as input |
| FR2  | Always run security vulnerability scan on every input |
| FR3  | Always run code quality check on every input |
| FR4  | Run REST API standards check only when route decorators are detected |
| FR5  | Synthesise tool outputs into a structured review (security / quality / API / verdict) |
| FR6  | Pause before finalising — human must approve or reject with feedback |
| FR7  | On rejection, incorporate feedback and re-synthesise |
| FR8  | On tool failure, retry up to MAX_TOOL_RETRIES=3; escalate with full context if still failing |
| FR9  | Emit a final formatted review report saved to `output/` |
| FR10 | Provide step-level observability via Portkey traces |

---

## Non-Functional Requirements

| ID   | Requirement |
|------|-------------|
| NFR1 | LLM calls routed through Portkey gateway (GPT-4o-mini via Azure OpenAI EUS2) |
| NFR2 | Tool failure should not crash the agent — escalation path required |
| NFR3 | pytest-asyncio suite must cover: normal flow, tool failure, escalation, human rejection |
| NFR4 | Human gate must be present before any state marked "complete" |
| NFR5 | Config loaded from `.env` — no credentials in source code |

---

## Success Definition

The agent produces a structured review report that:
- Correctly identifies at least 1 security issue in `sample_security_issue.py`
- Correctly identifies at least 1 quality issue in `sample_quality_issue.py`
- Correctly skips API standards check for non-route files
- Pauses for human approval and incorporates feedback
- Produces an escalation report when tools fail 3 times

---

## Technology Choices

| Component | Choice | Reason |
|-----------|--------|--------|
| Agent framework | LangGraph 0.2+ | Explicit state graph with interrupt support |
| LLM | GPT-4o-mini via Portkey | Perficient Academy gateway, tool-calling capable |
| Tools | Python functions with @tool decorator | LangChain tool protocol, mockable in tests |
| Memory | LangGraph MemorySaver (in-memory) | Session-scoped review history; no persistence needed |
| UI | Streamlit | Consistent with L1; easy to show human gate |
| Tests | pytest-asyncio | Required by L2 checklist |

---

## Out of Scope

- Connecting to a real GitHub/GitLab PR API (synthetic code snippets used instead)
- Persistent storage of reviews across sessions
- Webhook triggers
- Review posting to external systems (the "post" action is simulated/logged locally)
