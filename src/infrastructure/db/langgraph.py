"""LangGraph checkpoint-saver wiring.

The agent's per-booking context lives entirely in the LangGraph checkpoint saver (design D4).
``thread_id == booking_id``. In production a :class:`PostgresSaver` is used; tests inject an
:class:`InMemorySaver` so the suite stays green without a database.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from langgraph.checkpoint.postgres import PostgresSaver


@contextmanager
def postgres_saver(dsn: str) -> Iterator[PostgresSaver]:
    """Yield an initialized Postgres checkpoint saver, scoped to a connection.

    Creates the ``checkpoints`` / ``checkpoint_writes`` / ``checkpoint_blobs`` tables via
    ``setup()`` (idempotent) and closes the underlying connection on exit.

    Usage::

        with postgres_saver(settings.langgraph_dsn) as checkpointer:
            graph = build_negotiation_graph(checkpointer)
            ...  # worker lifetime
    """
    with PostgresSaver.from_conn_string(dsn) as saver:
        saver.setup()
        yield saver


def thread_config(booking_id: str) -> dict[str, Any]:
    """The LangGraph ``configurable`` mapping that pins a run to one booking's thread."""
    return {"configurable": {"thread_id": booking_id}}
