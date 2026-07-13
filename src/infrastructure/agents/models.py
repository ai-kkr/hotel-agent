"""Production chat-model construction.

Agents receive a ``langchain_core.language_models.BaseChatModel``. Production builds one from
:class:`Settings`; tests inject a deterministic fake (see ``tests/agents/fakes.py``).
"""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from infrastructure.config import Settings


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

    Unknown prefixes raise a clear configuration error rather than failing later inside an agent.
    """
    model = settings.llm_model
    if ":" not in model:
        return init_chat_model(model, model_provider="openai", temperature=0)

    provider, _, name = model.partition(":")
    match provider:
        case "openai":
            return init_chat_model(model, temperature=0)
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
            )
        case _:
            raise ValueError(
                f"unknown LLM provider {provider!r} in llm_model={model!r} "
                "(expected 'openai' or 'zai')"
            )
