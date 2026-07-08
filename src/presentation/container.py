"""Dependency container for the presentation layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from domain.application import InboundDispatcher, IntakeService
from domain.ports import InboundMailNormalizer, WorkflowGateway
from infrastructure.config import Settings


@dataclass
class WebhookDeps:
    """Wiring handed to the webhook router: provider signing key + collaborators."""

    signing_key: str
    normalizer: InboundMailNormalizer
    dispatcher: InboundDispatcher
    gateway: WorkflowGateway
    intake: IntakeService
    settings: Settings


def build_webhook_deps(
    settings: Settings,
    normalizer: InboundMailNormalizer,
    dispatcher: InboundDispatcher,
    gateway: WorkflowGateway,
    intake: IntakeService,
) -> WebhookDeps:
    signing_key = settings.mailgun_signing_key  # provider-specific; Mailgun on v1
    return WebhookDeps(
        signing_key=signing_key,
        normalizer=normalizer,
        dispatcher=dispatcher,
        gateway=gateway,
        intake=intake,
        settings=settings,
    )


def get_webhook_deps(request: Request) -> WebhookDeps:
    """Resolve the assembled :class:`WebhookDeps` from ``app.state``.

    Raises a 503 when the deps were not attached at app construction (e.g. boot without
    infrastructure wiring), preserving the long-standing "dependencies not configured" contract.
    """
    deps: WebhookDeps | None = getattr(request.app.state, "webhook_deps", None)
    if deps is None:
        raise HTTPException(status_code=503, detail="webhook dependencies not configured")
    return deps


# Reusable FastAPI dependency alias: ``deps: WebhookDepsDep`` in any path-operation signature.
WebhookDepsDep = Annotated[WebhookDeps, Depends(get_webhook_deps)]
