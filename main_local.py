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

    # Langfuse tracing is opt-in (KKR_LANGFUSE_ENABLED=true + keys). Empty list when off — the agents
    # then run with no callbacks, identical to pre-Langfuse behaviour.
    from infrastructure.observability import get_langfuse_callbacks

    langfuse_callbacks = get_langfuse_callbacks(settings)

    agents = build_agents(
        settings,
        model=model,
        checkpointer=checkpointer,
        searcher=searcher,
        fetcher=fetcher,
        langfuse_callbacks=langfuse_callbacks,
    )
    # The surface agent shares the negotiation stack's LLM + web backends + checkpointer. Wired into
    # the Telegram adapter only when KKR_TELEGRAM_BOT_TOKEN is set (design D10: bot may run separately).
    surface_components = SurfaceComponents(
        model=model,
        searcher=searcher,
        fetcher=fetcher,
        checkpointer=checkpointer,
        langfuse_callbacks=langfuse_callbacks,
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
    # Telegram inbound: aiogram Dispatcher polls Telegram and routes /start + messages to the surface
    # adapter (only when a bot token is configured). One polling process per token (Telegram rule).
    telegram_task: asyncio.Task[None] | None = None
    if runtime.telegram is not None and runtime.telegram_bot is not None:
        from infrastructure.telegram.run import start_telegram

        telegram_task = start_telegram(
            runtime.telegram_bot,
            runtime.telegram_dispatcher,
            surface_adapter=runtime.telegram,
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
        # Flush any queued Langfuse events before the process exits (no-op when tracing is off).
        from infrastructure.observability import shutdown_langfuse

        shutdown_langfuse()
        # Close the aiogram Bot session (releases its aiohttp client) if polling was wired.
        if runtime.telegram_bot is not None:
            await runtime.telegram_bot.session.close()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(run_local())
