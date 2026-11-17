# PR Code Review Agent — Task Checklist
**Written: 2026-11-17 | Follows plan.md**

## Phase 1 — Scaffold
- [x] T1.1: Create directory structure
- [x] T1.2: Write spec.md (problem, requirements, tech choices)
- [x] T1.3: Write plan.md (phase-by-phase)
- [x] T1.4: Write tasks.md (this file)
- [x] T1.5: Write requirements.txt
- [x] T1.6: Write .env.example
- [x] T1.7: Write src/config.py
- [x] T1.8: Write CLAUDE.md

## Phase 2 — Tool Layer
- [x] T2.1: Write scan_security_issues tool
- [x] T2.2: Write check_code_quality tool
- [x] T2.3: Write check_api_standards tool
- [x] T2.4: Add INJECT_FAILURE mode for deliberate failure testing
- [x] T2.5: Write data/standards/java_rest_standards.md
- [x] T2.6: Write data/samples/sample_secure.py
- [x] T2.7: Write data/samples/sample_security_issue.py
- [x] T2.8: Write data/samples/sample_quality_issue.py
- [x] T2.9: Write data/samples/sample_api_code.py

## Phase 3 — Agent
- [x] T3.1: Define ReviewState TypedDict
- [x] T3.2: Write analyze_node (LLM + tool binding)
- [x] T3.3: Wire ToolNode for tool execution
- [x] T3.4: Write track_errors_node
- [x] T3.5: Write synthesize_node
- [x] T3.6: Write human_gate_node
- [x] T3.7: Write generate_report_node
- [x] T3.8: Write handle_error_node
- [x] T3.9: Write routing functions
- [x] T3.10: Compile graph with interrupt_before + MemorySaver

## Phase 4 — CLI + UI
- [x] T4.1: Write src/cli.py with interrupt handling
- [x] T4.2: Write src/app.py Streamlit UI with approval buttons

## Phase 5 — Tests
- [x] T5.1: Write test_normal_review_happy_path
- [x] T5.2: Write test_security_findings_detected
- [x] T5.3: Write test_quality_findings_detected
- [x] T5.4: Write test_api_standards_skipped_for_non_route_code
- [x] T5.5: Write test_tool_failure_injection
- [x] T5.6: Write test_escalation_after_max_retries
- [x] T5.7: Write test_human_rejection_reruns_synthesis
- [x] T5.8: Write test_tool_error_count_increments
- [x] T5.9: Verify all tests pass

## Phase 6 — Evidence + Docs
- [x] T6.1: Capture normal run evidence
- [x] T6.2: Capture failure/escalation evidence
- [x] T6.3: Write docs/failure_analysis.md
- [x] T6.4: Write docs/ai_output_review.md
- [x] T6.5: Write docs/data_provenance.md
- [x] T6.6: Write docs/improvement_log.md
- [x] T6.7: Write docs/effort_statement.md
- [x] T6.8: Write docs/pitch_slide.md
- [x] T6.9: Write REFLECTION.md

## Phase 7 — Packaging
- [x] T7.1: Create Desktop/L2/ folder
- [x] T7.2: Create pr-review-agent.zip
- [x] T7.3: Create capstone_presentation.pptx
- [x] T7.4: Create Project_Demo_Guide.md
