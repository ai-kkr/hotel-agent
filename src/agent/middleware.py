"""Agent middleware that turns :class:`SelfCorrectionError` into agent guidance.

When a tool (e.g. ``send_wishes_to_hotel``) raises :class:`SelfCorrectionError` because the agent
skipped a required precondition, this middleware catches it and returns a ``ToolMessage``
describing the problem. The agent sees that message on its next turn and corrects course (ask the
user, fill in missing booking info, …) instead of crashing the graph.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain.agents.middleware.types import ExtendedModelResponse, ModelResponse
from langchain_core.messages import AIMessage, ToolMessage

from src.context import get_context
from src.logging import get_logger

from .context import EmailContext
from .exceptions import SelfCorrectionError
from .state import EmailState

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


class ModelSwitchingMiddleware(AgentMiddleware[EmailState, EmailContext, EmailState]):  # ty:ignore[invalid-type-arguments]
    async def awrap_model_call(
        self,
        request: ModelRequest[EmailContext],  # ty:ignore[invalid-type-arguments]
        handler: Callable[
            [ModelRequest[EmailContext]],  # ty:ignore[invalid-type-arguments]
            Awaitable[ModelResponse[EmailState]],
        ],
    ) -> ModelResponse[EmailState] | AIMessage | ExtendedModelResponse[EmailState]:

        ctx = request.runtime.context
        app_ctx = get_context()
        model_name = ctx.get("model_name")
        match model_name:
            case "glm-5.2":
                # do something for glm-5.2
                pass
            case _:
                return await super().awrap_model_call(request, handler)
        return await super().awrap_model_call(request, handler)


# @wrap_model_call
# def dynamic_model(
#     request: ModelRequest[EmailContext],  # ty:ignore[invalid-type-arguments]
#     handler: Callable[[ModelRequest], ModelResponse],
# ) -> ModelResponse:
#     context: EmailContext = request.runtime.context
#     model_name = context.get("model_name")
#     match model_name:
#         case "claude-haiku-4-5-20251001":
#             model = simple_model
#         case "claude-sonnet-4-6":
#             model = complex_model
#         case _:
#             return handler(request)
#     if len(request.messages) > 10:
#         model = complex_model
#     else:
#         model = simple_model
#     return handler(request.override(model=model))
