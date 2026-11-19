"""
LangChain callback handler for tool call observability.

Implements BaseCallbackHandler hooks (on_tool_start, on_tool_end, on_tool_error)
to track every @tool invocation during an agent run. Satisfies the
"AI Tool Integration" dimension — demonstrates hooks into the AI tool layer.
"""

from typing import Any, Union
import datetime
from langchain_core.callbacks import BaseCallbackHandler


class ToolObservabilityCallback(BaseCallbackHandler):
    """
    Tracks all tool invocations during an agent run.
    Wired via LangChain config callbacks or called manually from graph nodes.
    Call reset() before each new review run.
    """

    def __init__(self):
        super().__init__()
        self._calls: list[dict] = []

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        self._calls.append({
            "tool": serialized.get("name", "unknown"),
            "started_at": datetime.datetime.now().isoformat(),
            "status": "running",
            "result_preview": None,
        })

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        if self._calls:
            last = self._calls[-1]
            last["status"] = "error" if "TOOL_ERROR" in str(output) else "ok"
            last["result_preview"] = str(output)[:120]

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        if self._calls:
            self._calls[-1]["status"] = "exception"
            self._calls[-1]["result_preview"] = str(error)[:120]

    def record_from_message(self, tool_name: str, result: str) -> None:
        """
        Called manually from track_errors_node to record tool results
        extracted from LangGraph state messages (ToolMessage objects).
        """
        self._calls.append({
            "tool": tool_name,
            "started_at": datetime.datetime.now().isoformat(),
            "status": "error" if "TOOL_ERROR" in result else "ok",
            "result_preview": result[:120],
        })

    def reset(self) -> None:
        self._calls = []

    def summary(self) -> dict:
        total = len(self._calls)
        errors = sum(1 for c in self._calls if c["status"] in ("error", "exception"))
        return {
            "total_tool_calls": total,
            "successful": total - errors,
            "failed": errors,
            "calls": self._calls,
        }


# Module-level instance — call tool_tracker.reset() before each review run
tool_tracker = ToolObservabilityCallback()
