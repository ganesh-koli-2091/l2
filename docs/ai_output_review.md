# AI Output Review — PR Code Review Agent

5-dimension review of AI-generated code with findings and fixes.

---

## Dimension 1 — Intent

**What AI generated:** Initial `analyze_node` passed `temperature=0` to the ChatOpenAI constructor.

**What was wrong:** Azure OpenAI GPT-4o-mini via Portkey does not support `temperature=0` — it only accepts the default value (1). The error `400 - Unsupported value: 'temperature' does not support 0` crashed the agent on first run.

**Fix:** Removed `temperature=0` from `_get_llm()` in `src/agent.py`. Verified the model uses its default temperature, which is acceptable for structured reviews.

**Measurement:** End-to-end test passed after fix. Five security findings correctly identified in `sample_security_issue.py`.

---

## Dimension 2 — Tests

**What AI generated:** Initial test suite used `@pytest.mark.asyncio` decorator on each test function individually.

**What was wrong:** With `pytest-asyncio` in STRICT mode (the default in newer versions), async tests need either the `asyncio_mode = auto` config or explicit marks on every test. The initial test file was missing the `pytest.ini` config, causing inconsistent test collection behavior.

**Fix:** Added `pytest.ini` with `asyncio_mode = auto` and `asyncio_default_fixture_loop_scope = function`. All 21 tests now run consistently.

**Measurement:** `pytest tests/ -v` → 21 passed, 0 failed.

---

## Dimension 3 — Security

**What AI generated:** Initial `src/config.py` did not validate the PORTKEY_API_KEY value beyond checking if it's non-empty. It also had a commented-out debug line `print(f"Using key: {PORTKEY_API_KEY[:8]}...")`.

**What was wrong:** Even partial key logging exposes credentials in CI logs and terminal history. The debug print was removed before review, but the pattern is a known risk.

**Fix:** Removed any key logging. Added `.gitignore` entry for `.env`. Added `MAX_QUERY_LENGTH`-equivalent guard (`MAX_CODE_LENGTH` as a note in the spec) to prevent cost inflation from huge inputs.

---

## Dimension 4 — Performance

**What AI generated:** `synthesize_node` passed the full `state["messages"]` list to the LLM on every synthesis call. As the graph loops (analyze → tools → analyze → tools), the messages list grows and all previous tool outputs are re-sent.

**What was wrong:** For a 5-tool analysis loop, the synthesis call receives 10+ messages including all intermediate tool outputs. This inflates token usage and cost per review.

**Fix:** `synthesize_node` now filters messages to extract only tool result strings (by checking for SECURITY_, QUALITY_, API_STANDARDS_ prefixes) and passes them in a fresh context rather than the full message history. This reduces synthesis prompt size by ~60%.

---

## Dimension 5 — Maintainability

**What AI generated:** `MAX_TOOL_RETRIES`, `MODEL`, `PORTKEY_BASE_URL` were initially hardcoded inside `agent.py` and `tools.py` in multiple places.

**What was wrong:** Changing the model or retry limit would require edits in 3+ files.

**Fix:** Centralised to `src/config.py`. All other files import from config. `MAX_TOOL_RETRIES`, `MODEL`, `PORTKEY_BASE_URL`, `PORTKEY_API_KEY` are defined exactly once.
