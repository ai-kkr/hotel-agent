"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from presentation.api import router as api_router
from presentation.container import WebhookDeps
from presentation.webhooks import router as webhook_router


def create_app(*, webhook_deps: WebhookDeps | None = None) -> FastAPI:
    """Build the FastAPI app. ``webhook_deps`` is attached to ``app.state`` for the routers."""
    app = FastAPI(title="kkr-hotel-assist", version="0.1.0")
    if webhook_deps is not None:
        app.state.webhook_deps = webhook_deps
    app.include_router(webhook_router)
    app.include_router(api_router)
    return app
