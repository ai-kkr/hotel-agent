"""Agent middleware that turns :class:`SelfCorrectionError` into agent guidance.

When a tool (e.g. ``send_wishes_to_hotel``) raises :class:`SelfCorrectionError` because the agent
skipped a required precondition, this middleware catches it and returns a ``ToolMessage``
describing the problem. The agent sees that message on its next turn and corrects course (ask the
user, fill in missing booking info, …) instead of crashing the graph.
"""

from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from src.logging import get_logger

from .exceptions import SelfCorrectionError

__all__ = ["SelfCorrectionMiddleware"]

log = get_logger(__name__)


class SelfCorrectionMiddleware(AgentMiddleware):
    """Convert a tool's :class:`SelfCorrectionError` into a corrective ``ToolMessage``."""

    async def awrap_tool_call(  # type: ignore[override]
        self,
        request: Any,
        handler: Any,
    ) -> ToolMessage:
        try:
            return await handler(request)
        except SelfCorrectionError as e:
            # ``request.tool_call`` is a ToolCall TypedDict (a plain dict) in this langgraph
            # version — read it with item access, falling back to attribute access just in case.
            tool_call = request.tool_call
            if isinstance(tool_call, dict):
                tool_call_id = tool_call.get("id", "")
                tool_name = tool_call.get("name", "")
            else:
                tool_call_id = getattr(tool_call, "id", "")
                tool_name = getattr(tool_call, "name", "")
            log.warning("agent.self_correction", tool=tool_name, error=str(e))
            return ToolMessage(
                content=(
                    f"SelfCorrectionError: {e}. "
                    "Скорректируй следующее действие: уточни у пользователя или вызови "
                    "set_booking_info, чтобы заполнить недостающее."
                ),
                tool_call_id=tool_call_id,
            )
