import asyncio
from contextlib import asynccontextmanager, suppress

import fastapi

from src.bot.app import run_bot
from src.context import AppContext, get_context, set_context
from src.temporal.worker import run_worker

from . import webhook

__all__ = ["create_app"]


@asynccontextmanager
async def lifespan_event_handler(app: fastapi.FastAPI):
    """Lifespan event handler for FastAPI application.

    This function is called when the application starts and stops. It can be used to perform
    any necessary setup or teardown tasks, such as initializing resources or cleaning up
    connections.
    """
    ctx: AppContext = get_context()
    bot_task = asyncio.create_task(run_bot())
    worker, worker_task = await run_worker()
    try:
        yield
    finally:
        # Stop the polling task, then close the bot's aiohttp session. An unclosed session keeps
        # its connection pool alive on the loop and blocks uvicorn's graceful shutdown — that is
        # why the process hangs and needs a second Ctrl+C to exit.
        with suppress(asyncio.CancelledError):
            bot_task.cancel()
            await bot_task
        await ctx.bot.session.close()
        await worker.shutdown()
        with suppress(asyncio.CancelledError):
            worker_task.cancel()
            await worker_task
        # Flush queued Langfuse events so no traces are lost on exit (no-op if never enabled).
        from src.agent.tracing import shutdown_langfuse

        shutdown_langfuse()


def create_app(context: AppContext) -> fastapi.FastAPI:
    set_context(context)
    app = fastapi.FastAPI(lifespan=lifespan_event_handler)
    app.include_router(webhook.router)
    return app
