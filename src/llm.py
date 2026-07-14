"""Production chat-model construction.

Agents receive a ``langchain_core.language_models.BaseChatModel``. Production builds one from
:class:`Settings`; tests inject a deterministic fake.
"""

from __future__ import annotations

from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from src.config import Settings


def build_model(
    settings: Settings,
    model_override: str | None = None,
) -> BaseChatModel:
    """Build the chat model from settings.

    ``llm_model`` is a fully-qualified ``"<provider>:<model>"`` string or a bare model name
    (provider inferred as ``openai``). Supported providers:

    - ``openai`` (default) — e.g. ``openai:gpt-4o-mini`` or bare ``gpt-4o-mini``.
    - ``zai`` — Z.AI (OpenAI-compatible), e.g. ``zai:glm-5.2``; routed through the OpenAI adapter
      with ``base_url = settings.zai_api_base`` and ``api_key = settings.zai_api_key``.
    - ``openrouter`` — OpenRouter (OpenAI-compatible aggregator), e.g.
      ``openrouter:anthropic/claude-3.5-sonnet``; routed through the OpenAI adapter with
      ``base_url = settings.openrouter_api_base`` and ``api_key = settings.openrouter_api_key``.

    Unknown prefixes raise a clear configuration error rather than failing later inside an agent.

    ``timeout`` and ``max_retries`` are applied to every provider's chat model. Because all
    supported providers route through the OpenAI-compatible adapter, this also covers the direct
    ``model.ainvoke`` call in ``_compose_letter`` (which bypasses agent middleware).
    """
    model = settings.llm_model
    # Common kwargs for every provider: request timeout + HTTP retry budget.
    common: dict[str, Any] = {
        "timeout": settings.llm_timeout_seconds or None,
        "max_retries": settings.llm_max_retries,
    }
    if ":" not in model:
        return init_chat_model(model, model_provider="openai", temperature=0, **common)

    provider, _, name = model.partition(":")
    match provider:
        case "openai":
            return init_chat_model(model, temperature=0, **common)
        case "zai":
            if not settings.zai_api_key:
                raise ValueError(
                    "KKR_ZAI_API_KEY is required when KKR_LLM_MODEL uses the 'zai:' provider"
                )
            return init_chat_model(
                f"openai:{model_override or name}",
                temperature=0,
                base_url=settings.zai_api_base,
                api_key=settings.zai_api_key,
                **common,
            )
        case "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError(
                    "KKR_OPENROUTER_API_KEY is required when KKR_LLM_MODEL uses the "
                    "'openrouter:' provider"
                )
            # ``reasoning_effort`` is sent top-level; OpenRouter maps it to per-model thinking
            # controls (e.g. Gemini ``thinkingLevel``). Applied only here — zai/openai may reject
            # the unknown field. ``None`` => provider default.
            kwargs: dict[str, Any] = {
                "temperature": 0,
                "base_url": settings.openrouter_api_base,
                "api_key": settings.openrouter_api_key,
                **common,
            }
            if settings.openrouter_reasoning_effort:
                kwargs["reasoning_effort"] = settings.openrouter_reasoning_effort
            return init_chat_model(f"openai:{model_override or name}", **kwargs)
        case _:
            raise ValueError(
                f"unknown LLM provider {provider!r} in llm_model={model!r} "
                "(expected 'openai', 'zai', or 'openrouter')"
            )
