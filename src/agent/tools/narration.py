"""User-facing narration / control tools: ``inform_step`` and ``cancel_task``."""

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import Command

from src.logging import get_logger

from ..context import EmailContext
from ..state import EmailState
from ..types import MessageText
from ..utils import send_telegram_reply
from .utils import ack

__all__ = ["cancel_task", "inform_step"]

log = get_logger(__name__)


@tool
async def inform_step(step: str, runtime: ToolRuntime[EmailContext, EmailState]):
    """Narrate a progress step to the user (no state side-effect besides the ack).

    Use this to keep the user informed about what you are doing, e.g. "Looking up the hotel
    contact email…". Do not abuse it — one short message per meaningful step.

    Args:
        step: A short description of the current step.
    """
    log.info("tool.inform_step", step=step)
    await send_telegram_reply(step)
    return Command(update={"messages": [ack(runtime)]})


@tool
async def cancel_task(reason: str, runtime: ToolRuntime[EmailContext, EmailState]):
    """Cancel the task — something blocking made it impossible to proceed.

    Use when the hotel email cannot be found or the user declined to continue. The reason is
    surfaced to the user.

    Args:
        reason: A short explanation of why the task is being cancelled.
    """
    log.info("tool.cancel_task", reason=reason)
    runtime.stream_writer(MessageText(text="Задача отменена: " + reason))
    return Command(
        update={
            "task_cancelled": True,
            "messages": [ack(runtime, content="Task cancelled")],
        }
    )
