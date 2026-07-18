"""Langfuse tracing wiring for the LangGraph agent.

Langfuse is self-hosted via docker compose (UI at ``KKR_LANGFUSE_HOST``). Tracing is opt-in: it
activates only when ``KKR_LANGFUSE_ENABLED=true`` AND both project keys are set, so local/test runs
without the Langfuse stack stay clean.

The Langfuse v3+ ``CallbackHandler`` is attached per agent node inside the Temporal-wrapped graph
(:func:`src.agent.agent._langfuse_handler`) via ``var_child_runnable_config``. Each turn becomes one
trace (the trace id is derived from the workflow run id and shared by every node in the turn); trace
attributes (``langfuse_user_id`` / ``langfuse_session_id``) are set on the config metadata by the
workflow.

The ``Langfuse`` client is a process-wide singleton; :func:`init_langfuse` configures it once at
startup, :func:`shutdown_langfuse` flushes on shutdown.
"""

from __future__ import annotations

from src.config import Settings, get_settings
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


def _is_enabled(settings: Settings) -> bool:
    return bool(
        settings.langfuse_enabled and settings.langfuse_public_key and settings.langfuse_secret_key
    )
