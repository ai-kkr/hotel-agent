"""Shared helpers for the agent tools."""

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage

from ..context import EmailContext
from ..state import EmailState

__all__ = ["ack"]


def ack(
    runtime: ToolRuntime[EmailContext, EmailState], content: str = "Success"
) -> ToolMessage:
    """Build the acknowledgement ``ToolMessage`` that closes a tool call in the agent's history."""
    return ToolMessage(content=content, tool_call_id=runtime.tool_call_id)
