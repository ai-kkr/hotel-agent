"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from presentation.api import router as api_router
from presentation.container import WebhookDeps
from presentation.local_debug import router as local_debug_router
from presentation.webhooks import router as webhook_router


def create_app(*, webhook_deps: WebhookDeps | None = None) -> FastAPI:
    """Build the FastAPI app. ``webhook_deps`` is attached to ``app.state`` for the routers.

    Telegram inbound polling is **not** part of the app lifecycle: it is driven by
    ``main_local.run_local`` (an asyncio task on the aiogram Dispatcher), mirroring how the Temporal
    worker task is managed. Keeping it out of the app keeps ``create_app`` free of Telegram concerns.
    """
    app = FastAPI(title="kkr-hotel-assist", version="0.1.0")
    if webhook_deps is not None:
        app.state.webhook_deps = webhook_deps
    app.include_router(webhook_router)
    app.include_router(api_router)
    app.include_router(local_debug_router)
    return app
