"""LLM observability wiring (Langfuse).

Thin wrapper over the Langfuse v3 SDK that the LangGraph agents use to publish traces. Tracing is
gated by ``Settings.langfuse_enabled`` plus the presence of keys, so environments without the
Langfuse stack (tests, vanilla local runs) get an empty callback list and behave exactly as before.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from infrastructure.config import Settings


def get_langfuse_callbacks(settings: Settings) -> list[Callable[..., Any]]:
    """Return the Langfuse LangChain ``CallbackHandler`` list to pass in an invoke ``config``.

    Returns an empty list when tracing is disabled (off by default, or keys missing) — agents then
    run with no callbacks, identical to pre-Langfuse behaviour. When enabled, the Langfuse client
    is initialized once (SDK singleton) and a single handler is reused across all agent invocations.

    The SDK reads its credentials from ``LANGFUSE_PUBLIC_KEY`` / ``LANGFUSE_SECRET_KEY`` /
    ``LANGFUSE_HOST`` env vars, so we mirror our ``KKR_LANGFUSE_*`` settings onto them *before* the
    first ``get_client()`` call (the SDK never returns ``None`` — it lazily builds the singleton from
    the env, so the env must be set first or it initializes a disabled client).
    """
    if not settings.langfuse_enabled or not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return []

    import os

    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key or "")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key or "")
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

    # Imported lazily so the (optional) langfuse dependency is never required to import this module.
    from langfuse import get_client
    from langfuse.langchain import CallbackHandler

    get_client()  # initializes the singleton from the env vars set above
    return [CallbackHandler()]


def shutdown_langfuse() -> None:
    """Flush the background event queue on shutdown (safe no-op when tracing was never enabled)."""
    try:
        from langfuse import get_client
    except Exception:
        return  # langfuse not installed / not imported — nothing to flush.
    client = get_client()
    if client is not None:
        client.flush()
