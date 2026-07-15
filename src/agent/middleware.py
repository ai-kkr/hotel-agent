"""Agent middleware that turns :class:`SelfCorrectionError` into agent guidance.

When a tool (e.g. ``send_wishes_to_hotel``) raises :class:`SelfCorrectionError` because the agent
skipped a required precondition, this middleware catches it and returns a ``ToolMessage``
describing the problem. The agent sees that message on its next turn and corrects course (ask the
user, fill in missing booking info, …) instead of crashing the graph.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain.agents.middleware.types import ExtendedModelResponse, ModelResponse
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import ValidationError

from src.config import ToolRetryConfig, ToolRetryPolicy
from src.logging import get_logger

from .context import EmailContext
from .exceptions import SelfCorrectionError
from .state import EmailState

__all__ = ["SelfCorrectionMiddleware", "ToolRetryMiddleware"]

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


#: Exception types that represent a deterministic / logic failure, never a transient blip. Retrying
#: these would just re-raise the same error, so they bypass the retry loop entirely. Note that
#: :class:`SelfCorrectionError` is in here too — it is handled upstream by
#: :class:`SelfCorrectionMiddleware` and must never be retried (a tool re-invocation would just
#: re-fail the same precondition).
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
    # We deliberately err toward retrying rather than maintaining an allowlist of every client's
    # exception types; deterministic logic errors are already excluded above.
    return not isinstance(exc, _DETERMINISTIC_ERRORS)


def _backoff_delay(policy: ToolRetryPolicy, attempt: int) -> float:
    """Exponential backoff for ``attempt`` (0-indexed), capped at ``max_delay`` + optional jitter."""
    delay = min(policy.initial_delay * (policy.backoff_factor**attempt), policy.max_delay)
    if policy.jitter and delay > 0:
        delay *= random.uniform(0.75, 1.25)  # jitter, not crypto
    return max(delay, 0.0)


class ToolRetryMiddleware(AgentMiddleware):
    """Retry failing tool calls with per-tool policies.

    Each tool gets its own :class:`ToolRetryPolicy` (from :class:`ToolRetryConfig`, sourced from
    ``config.yaml``): a mail-sending tool should not retry (an intermittent success would send the
    letter twice), while a network tool (``search_internet``, ``extract_web_page``) benefits from
    a few retries with exponential backoff.

    Sits *inside* :class:`SelfCorrectionMiddleware` in the middleware chain: a
    :class:`SelfCorrectionError` raised by the tool propagates straight through this middleware
    (it's in :data:`_DETERMINISTIC_ERRORS`) and is caught by the self-correction layer. When all
    retries are exhausted the failure is surfaced to the agent as a ``ToolMessage`` (rather than
    crashing the turn), so the agent can tell the guest something went wrong.
    """

    def __init__(self, config: ToolRetryConfig) -> None:
        super().__init__()
        self.config = config

    def _policy_for(self, tool_name: str) -> ToolRetryPolicy:
        return self.config.overrides.get(tool_name, self.config.default)

    async def awrap_tool_call(  # type: ignore[override]
        self,
        request: Any,
        handler: Any,
    ) -> Any:
        tool_call = request.tool_call
        if isinstance(tool_call, dict):
            tool_name = tool_call.get("name", "")
            tool_call_id = tool_call.get("id", "")
        else:
            tool_name = getattr(tool_call, "name", "")
            tool_call_id = getattr(tool_call, "id", "")

        policy = self._policy_for(tool_name)
        last_exc: BaseException | None = None
        # Initial attempt + up to ``max_retries`` retries.
        for attempt in range(policy.max_retries + 1):
            try:
                return await handler(request)
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


class OpenRouterStickySessionMiddleware(AgentMiddleware):
    """Inject OpenRouter ``session_id`` for sticky routing → prompt-cache locality.

    OpenRouter uses ``session_id`` as an explicit sticky-routing key: when present, every turn of
    a conversation is routed to the same provider endpoint, so Gemini's prompt cache stays warm
    from the very first request (without ``session_id`` sticky routing only kicks in after a cache
    hit is observed). See https://openrouter.ai/docs/guides/best-practices/prompt-caching.

    The session id is derived from ``EmailContext.client_id`` — stable per conversation, distinct
    per client (same shape as the LangGraph ``thread_id`` ``client:{id:04d}``), well under the
    256-char cap. It's sent as a top-level ``extra_body`` field: ``model_settings`` is unpacked
    into ``model.bind_tools(**model_settings)``, and the OpenAI SDK merges ``extra_body`` into the
    HTTP request body at the top level — exactly where OpenRouter reads ``session_id``.

    Gated to OpenRouter only (checks ``model.openai_api_base``): an unknown ``extra_body`` field
    could error against the real OpenAI / Z.AI endpoints, so we leave those providers untouched.
    """

    async def awrap_model_call(  # type: ignore[override]
        self,
        request: ModelRequest[EmailContext],  # ty:ignore[invalid-type-arguments]
        handler: Callable[
            [ModelRequest[EmailContext]],  # ty:ignore[invalid-type-arguments]
            Awaitable[ModelResponse[EmailState]],
        ],
    ) -> ModelResponse[EmailState] | AIMessage | ExtendedModelResponse[EmailState]:
        base_url = str(getattr(request.model, "openai_api_base", "") or "")
        if "openrouter.ai" not in base_url:
            return await handler(request)

        client_id = request.runtime.context.get("client_id")
        if client_id is None:
            return await handler(request)

        session_id = f"client:{client_id:04d}"
        # Merge into any pre-existing extra_body rather than clobbering it.
        extra_body = {**(request.model_settings.get("extra_body") or {}), "session_id": session_id}
        settings = {**request.model_settings, "extra_body": extra_body}
        return await handler(request.override(model_settings=settings))
