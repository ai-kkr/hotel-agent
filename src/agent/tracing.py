"""Langfuse tracing wiring for the LangGraph agent.

Langfuse is self-hosted via docker compose (UI at ``KKR_LANGFUSE_HOST``). Tracing is opt-in: it
activates only when ``KKR_LANGFUSE_ENABLED=true`` AND both project keys are set, so local/test runs
without the Langfuse stack stay clean.

We use the Langfuse v3+ ``CallbackHandler`` — attached per agent turn via the LangChain
``RunnableConfig``. Each agent turn becomes one trace. Trace attributes are passed through the
config ``metadata`` (the keys the callback reads are prefixed ``langfuse_``):

- ``langfuse_user_id``    — the client id (who the conversation is with).
- ``langfuse_session_id`` — the per-client LangGraph thread id, so a guest's whole back-and-forth
  groups into a single session in the Langfuse UI.
- ``langfuse_tags``       — a tag distinguishing the entry point (``telegram``).

The ``Langfuse`` client is a process-wide singleton; :func:`init_langfuse` configures it once at
startup, :func:`shutdown_langfuse` flushes on shutdown.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from src.config import Settings, get_settings
from src.db.models import ClientORM
from src.logging import get_logger

log = get_logger(__name__)

_initialized = False


def init_langfuse(settings: Settings | None = None) -> None:
    """Configure the process-wide Langfuse client (idempotent; safe to call more than once).

    No-op when tracing is disabled; instantiates ``Langfuse(...)`` once when enabled. The Langfuse
    SDK keeps a module-level singleton returned by ``get_client()`` — instantiating the class
    registers it.
    """
    global _initialized
    if _initialized:
        return
    settings = settings or get_settings()
    if not _is_enabled(settings):
        log.info("langfuse.disabled")
        _initialized = True
        return

    from langfuse import Langfuse

    Langfuse(
        host=settings.langfuse_host,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
    )
    _initialized = True
    log.info("langfuse.enabled", host=settings.langfuse_host)


def shutdown_langfuse() -> None:
    """Flush queued events to Langfuse on app shutdown so no traces are lost."""
    global _initialized
    if not _initialized:
        return
    from langfuse import get_client

    get_client().flush()
    _initialized = False


def with_tracing(
    base: RunnableConfig,
    client: ClientORM,
    *,
    settings: Settings | None = None,
) -> RunnableConfig:
    """Return ``base`` enriched with a Langfuse callback + trace metadata, or unchanged.

    Returns ``base`` as-is when tracing is disabled, so the call sites don't need their own guards.
    """
    settings = settings or get_settings()
    if not _is_enabled(settings):
        return base

    from langfuse.langchain import CallbackHandler

    handler = CallbackHandler()
    metadata = dict(base.get("metadata") or {})
    metadata.update(
        {
            "langfuse_user_id": str(client.id),
            "langfuse_session_id": client.thread_id,
        }
    )
    callbacks = list(base.get("callbacks") or [])  # ty:ignore[invalid-argument-type]
    callbacks.append(handler)
    return {**base, "callbacks": callbacks, "metadata": metadata}  # type: ignore[return-value]


def _is_enabled(settings: Settings) -> bool:
    return bool(
        settings.langfuse_enabled and settings.langfuse_public_key and settings.langfuse_secret_key
    )
