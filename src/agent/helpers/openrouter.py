"""OpenRouter-specific chat-model config for the agent's model node.

OpenRouter uses ``session_id`` as an explicit sticky-routing key: every turn of a conversation
routes to the same provider endpoint, keeping the prompt cache warm from the first request. We pass
it as ``extra_body`` for ``bind_tools`` (the OpenAI SDK merges ``extra_body`` into the HTTP body at
the top level, exactly where OpenRouter reads it).

Gated to OpenRouter by checking the model's base URL — an unknown ``extra_body`` field could error
against real OpenAI / Z.AI endpoints. Takes a bare ``client_id`` (``None`` when unknown) so it has
no dependency on :class:`EmailContext` / :class:`Runtime`.
"""

from langchain.chat_models import BaseChatModel


def sticky_session_kwargs(model: BaseChatModel, client_id: int | None) -> dict:
    """``bind_tools`` kwargs carrying the OpenRouter ``session_id``, or ``{}`` when not applicable.

    Returns an empty dict (→ no extra bind kwargs) for non-OpenRouter providers or when there is no
    client id.
    """
    base_url = str(getattr(model, "openai_api_base", "") or "")
    if "openrouter.ai" not in base_url:
        return {}
    if client_id is None:
        return {}
    return {"extra_body": {"session_id": f"client:{client_id:04d}"}}
