"""Langfuse callback wiring for the agent's graph nodes.

The Langfuse v3+ ``CallbackHandler`` is attached per node through ``var_child_runnable_config`` so
every node activity in one agent turn links its root run to a single Langfuse trace (the trace id is
read from the config metadata, set by the workflow from its stable run id). Gated on
:func:`src.agent.tracing._is_enabled` so a keyless client is never touched when Langfuse is off —
no SDK "initialized without public_key" warning on local/test runs.
"""

from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from functools import wraps

from langchain_core.runnables.config import var_child_runnable_config
from langfuse.langchain import CallbackHandler


def langfuse_handler() -> CallbackHandler | None:
    """Build a callback handler bound to the turn's trace id, or ``None`` if tracing is disabled.

    Built per call (not cached): the trace id differs per turn, and construction is cheap
    (``get_client()`` returns the process singleton).
    """
    from src.agent.tracing import _is_enabled
    from src.config import get_settings

    if not _is_enabled(get_settings()):
        return None
    cfg = var_child_runnable_config.get() or {}
    trace_id = (cfg.get("metadata") or {}).get("langfuse_trace_id")
    if trace_id:
        return CallbackHandler(trace_context={"trace_id": trace_id})
    return CallbackHandler()


@asynccontextmanager
async def inject_langfuse_callback():
    """Append a :func:`langfuse_handler` to the current runnable config for the duration of the block."""
    handler = langfuse_handler()
    if handler is None:  # tracing disabled — nothing to attach
        yield
        return
    cfg = var_child_runnable_config.get() or {}
    # Merge the handler onto the existing callbacks. Under the Temporal LangGraph plugin (production)
    # ``callbacks`` is a list (model_node etc. run fine); but a plain ``graph.ainvoke`` may set an
    # ``AsyncCallbackManager`` there, which isn't iterable — ``[*list(manager), ...]`` would crash with
    # ``TypeError: object is not iterable``. Handle both: append to a list, otherwise replace.
    existing = cfg.get("callbacks", [])
    new_callbacks: list = (
        [*existing, handler] if isinstance(existing, list | tuple) else [handler]
    )
    cfg = cfg | {"callbacks": new_callbacks}
    token = var_child_runnable_config.set(cfg)
    try:
        yield
    finally:
        var_child_runnable_config.reset(token)


def with_langfuse[**P, R](
    node: Callable[P, Coroutine[R, None, R]],
) -> Callable[P, Coroutine[R, None, R]]:
    """Decorate an agent node so a Langfuse callback is attached to its model/tool calls."""

    @wraps(node)
    async def wrapped(*a: P.args, **kw: P.kwargs) -> R:
        async with inject_langfuse_callback():
            return await node(*a, **kw)

    return wrapped
