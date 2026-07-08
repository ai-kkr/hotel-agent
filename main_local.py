"""Local entrypoint: run the API + Temporal worker + agents in one process with stub mail.

Usage::

    docker compose up -d                       # Temporal + Postgres
    uv run alembic upgrade head                # domain schema
    cp .env.example .env  && edit (KKR_ZAI_API_KEY, KKR_LLM_MODEL=zai:glm-5.2, ...)
    uv run python main_local.py

Then POST a stub inbound webhook to ``/webhooks/mailgun/inbound`` (provider route is provider-name
based; the stub normalizer parses the same payload shape without signature) and inspect the stub
outbox in the logs (``event=outbound.stub.recorded``).

Graceful shutdown: uvicorn installs SIGINT/SIGTERM handlers; on exit the Temporal worker task is
cancelled and the httpx client / DB engine are closed.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

import httpx
import uvicorn
from langgraph.checkpoint.memory import InMemorySaver

from infrastructure.agents.factory import build_agents
from infrastructure.agents.models import build_model
from infrastructure.agents.surface import SurfaceComponents
from infrastructure.agents.tools import FakeWebSearcher, HttpxWebFetcher
from infrastructure.config import get_settings
from infrastructure.db.session import create_engine, session_factory
from infrastructure.logging import configure_logging
from infrastructure.runtime import build_local_app
from infrastructure.workflows.worker import build_client


async def run_local() -> None:
    settings = get_settings()
    configure_logging()

    engine = create_engine(settings.postgres_dsn)
    session_maker = session_factory(engine)
    temporal_client = await build_client(settings)

    model = build_model(settings)
    checkpointer = InMemorySaver()  # zero-setup local checkpoints; swap to PostgresSaver for prod-parity
    # Web search has no keyless public backend; FakeWebSearcher is a local placeholder.
    # Swap for HttpxWebSearcher(endpoint=..., api_key=...) to exercise the discoverer for real.
    searcher = FakeWebSearcher()
    fetcher = HttpxWebFetcher()

    agents = build_agents(
        settings,
        model=model,
        checkpointer=checkpointer,
        searcher=searcher,
        fetcher=fetcher,
    )
    # The surface agent shares the negotiation stack's LLM + web backends + checkpointer. Wired into
    # the Telegram adapter only when KKR_TELEGRAM_BOT_TOKEN is set (design D10: bot may run separately).
    surface_components = SurfaceComponents(
        model=model, searcher=searcher, fetcher=fetcher, checkpointer=checkpointer
    )

    http_client = httpx.AsyncClient()
    runtime = build_local_app(
        settings,
        temporal_client=temporal_client,
        agents=agents,
        session_maker=session_maker,
        http_client=http_client,
        surface_components=surface_components,
    )

    config = uvicorn.Config(runtime.app, host="127.0.0.1", port=8000, loop="asyncio", log_config=None)
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve(), name="uvicorn")
    worker_task = asyncio.create_task(runtime.worker.run(), name="temporal-worker")
    # Telegram inbound: long-poll getUpdates → surface agent (only when a bot token is configured).
    telegram_task: asyncio.Task[None] | None = None
    if runtime.telegram is not None:
        from infrastructure.telegram.polling import run_telegram

        telegram_task = asyncio.create_task(
            run_telegram(runtime.telegram, poll_timeout=settings.telegram_poll_timeout_seconds),
            name="telegram-poll",
        )
    try:
        # server.serve() returns on SIGINT/SIGTERM (uvicorn installs its own handlers).
        await server_task
    except asyncio.CancelledError:
        # Ctrl+C: asyncio.run() cancels all tasks; swallow the noise and shut down cleanly.
        pass
    finally:
        if telegram_task is not None:
            telegram_task.cancel()
        worker_task.cancel()
        await http_client.aclose()
        await engine.dispose()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(run_local())
