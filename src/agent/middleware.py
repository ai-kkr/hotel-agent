"""Tool-call helpers: retry transient failures, turn :class:`SelfCorrectionError` into guidance.

These used to be ``create_agent`` middlewares (``SelfCorrectionMiddleware`` /
``ToolRetryMiddleware``). The agent now runs under Temporal via a hand-built :class:`StateGraph`
(no ``create_agent``), so the same behaviour is applied inside the tool-call wrapper
(:func:`src.agent.agent._tool_wrapper`) using :func:`run_tool_call` here.

Behaviour per tool call (matches the old middleware stack, ``SelfCorrection`` outermost →
``ToolRetry`` innermost):

- a tool raising :class:`SelfCorrectionError` (a violated precondition, e.g. sending without full
  booking) → return a corrective ``ToolMessage``; the agent corrects course on its next turn
  instead of crashing;
- a transient failure (network blip, provider 5xx, …) → retried per the tool's
  :class:`ToolRetryPolicy` with exponential backoff, and surfaced as a ``ToolMessage`` when the
  budget is exhausted (mail-sending tools have ``max_retries=0`` so a late success can't send the
  letter twice);
- a deterministic logic error that isn't self-correction (``ValueError``/``TypeError``/…) →
  re-raised, exactly as before.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable

from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from pydantic import ValidationError

from src.config import ToolRetryConfig, ToolRetryPolicy
from src.logging import get_logger

from .exceptions import SelfCorrectionError

__all__ = ["ToolExecutor", "run_tool_call"]

log = get_logger(__name__)


#: A tool execution callable as passed by ``ToolNode.awrap_tool_call``: takes the parsed request and
#: returns the tool's result (a ``ToolMessage`` for plain tools, or a ``Command`` for state-mutating
#: ones).
type ToolExecutor = Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]]


#: Exception types that represent a deterministic / logic failure, never a transient blip. Retrying
#: these would just re-raise the same error, so they bypass the retry loop. :class:`SelfCorrectionError`
#: is caught earlier (above the generic handler) and turned into guidance, never retried.
_DETERMINISTIC_ERRORS: tuple[type[BaseException], ...] = (
    SelfCorrectionError,
    ValidationError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    IndexError,
)


def _is_retryable(exc: BaseException, *, mode: str) -> bool:
    """Whether ``exc`` should be retried under the given ``mode`` (``transient`` or ``all``)."""
    if isinstance(exc, _DETERMINISTIC_ERRORS):
        return False
    if mode == "all":
        return True
    # ``transient``: retry anything non-deterministic (network blips, provider 5xx, timeouts, …).
    return not isinstance(exc, _DETERMINISTIC_ERRORS)


def _backoff_delay(policy: ToolRetryPolicy, attempt: int) -> float:
    """Exponential backoff for ``attempt`` (0-indexed), capped at ``max_delay`` + optional jitter."""
    delay = min(policy.initial_delay * (policy.backoff_factor**attempt), policy.max_delay)
    if policy.jitter and delay > 0:
        delay *= random.uniform(0.75, 1.25)  # jitter, not crypto
    return max(delay, 0.0)


def _tool_call_refs(request: ToolCallRequest) -> tuple[str, str]:
    """``(tool_call_id, tool_name)`` from the request — ``tool_call`` is a ``ToolCall`` TypedDict."""
    tool_call = request.tool_call
    return tool_call.get("id") or "", tool_call["name"]


async def run_tool_call(
    request: ToolCallRequest,
    execute: ToolExecutor,
    *,
    config: ToolRetryConfig,
) -> ToolMessage | Command:
    """Run one tool call with per-tool retry + self-correction, never crashing the turn.

    ``execute(request)`` invokes the tool. ``config`` is the per-tool retry config from
    ``config.yaml``. Returns whatever the tool returns (a ``ToolMessage`` or ``Command``), or a
    synthesised ``ToolMessage`` when the tool self-corrected or exhausted its retries.
    """
    tool_call_id, tool_name = _tool_call_refs(request)
    policy = config.overrides.get(tool_name, config.default)
    last_exc: BaseException | None = None
    # Initial attempt + up to ``max_retries`` retries.
    for attempt in range(policy.max_retries + 1):
        try:
            return await execute(request)
        except SelfCorrectionError as e:
            # Precondition violated — tell the agent how to fix it; never retry (it would just
            # re-fail the same precondition).
            log.warning("agent.self_correction", tool=tool_name, error=str(e))
            return ToolMessage(
                content=(
                    f"SelfCorrectionError: {e}. "
                    "Скорректируй следующее действие: уточни у пользователя или вызови "
                    "set_booking_info, чтобы заполнить недостающее."
                ),
                tool_call_id=tool_call_id,
            )
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc, mode=policy.retry_on):
                raise
            if attempt >= policy.max_retries:
                break
            delay = _backoff_delay(policy, attempt)
            log.warning(
                "agent.tool_retry",
                tool=tool_name,
                attempt=attempt + 1,
                max_retries=policy.max_retries,
                delay=round(delay, 3),
                error=str(exc),
            )
            await asyncio.sleep(delay)

    # Retries exhausted: surface a ToolMessage so the agent can react instead of crashing.
    attempts = policy.max_retries + 1
    log.error(
        "agent.tool_retry_exhausted",
        tool=tool_name,
        attempts=attempts,
        error=str(last_exc),
    )
    return ToolMessage(
        content=(
            f"Tool '{tool_name}' failed after {attempts} attempt(s): {last_exc}. "
            "Сообщи пользователю, что действие не удалось, и при необходимости попробуй "
            "альтернативу."
        ),
        tool_call_id=tool_call_id,
    )
