"""Local-run wiring: assemble the FastAPI app + Temporal worker with stub mail (no Mailgun).

This is the developer-facing counterpart to ``main_experiment.py`` (which wires the production
Mailgun stack). In local mode:

- mail adapters are the **stub** (``KKR_MAIL_PROVIDER=stub``) — outbound emails land in an in-memory
  outbox, inbound webhooks need no signature;
- Temporal is expected to run in Docker (``docker compose up``) at ``settings.temporal_target``;
- Postgres is expected at ``settings.postgres_dsn`` / ``settings.langgraph_dsn`` (also in the compose
  stack);
- LangGraph uses an ``InMemorySaver`` by default for a zero-setup checkpoint store (the design's open
  question D5 — swap to ``PostgresSaver`` to be closer to prod).

``build_local_app`` is pure assembly given the "heavy" collaborators (Temporal client, agents,
DB session factory); ``main_local.run_local`` connects the real ones and runs worker + API in one
process. The split keeps the wiring unit-testable without Temporal / LLM / DB.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio.client import Client
from temporalio.worker import Worker

from domain.application import InboundDispatcher, IntakeService
from infrastructure.agents.factory import AgentBundle
from infrastructure.config import Settings
from infrastructure.logging import get_logger
from infrastructure.mail.factory import build_inbound_normalizer, build_outbound_gateway
from infrastructure.mail.notifier import EmailClientNotifier
from infrastructure.mail.stub import StubOutboundGateway
from infrastructure.persistence.sqlalchemy_repos import (
    SqlAlchemyBookingRepository,
    SqlAlchemyClientRepository,
)
from infrastructure.workflows.activities import ConciergeActivities
from infrastructure.workflows.temporal_gateway import TemporalWorkflowGateway
from infrastructure.workflows.worker import build_worker
from presentation.app import create_app
from presentation.container import build_webhook_deps

_logger = get_logger(__name__)


@dataclass
class LocalRuntime:
    """The assembled local process: app + worker + resources to release on shutdown."""

    app: FastAPI
    worker: Worker
    temporal_client: Client
    http_client: httpx.AsyncClient
    outbox_gateway: StubOutboundGateway


def build_local_app(
    settings: Settings,
    *,
    temporal_client: Client,
    agents: AgentBundle,
    session_maker: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient | None = None,
    worker: Worker | None = None,
) -> LocalRuntime:
    """Assemble the FastAPI app + Temporal worker with stub mail collaborators.

    Pure and synchronous: caller supplies the already-connected Temporal client, the built agent
    bundle, and a DB session factory. Returns a :class:`LocalRuntime` whose ``worker`` is created but
    not started (``run_local`` starts it). Pass ``worker`` to inject a fake (tests) instead of
    constructing a real :class:`Worker` from ``temporal_client``.
    """
    if settings.mail_provider != "stub":
        # Local mode is stub-only by design; guard against accidental Mailgun wiring locally.
        raise ValueError(
            f"local runtime requires KKR_MAIL_PROVIDER=stub, got {settings.mail_provider!r}"
        )

    client_http = http_client or httpx.AsyncClient()
    clients_repo = SqlAlchemyClientRepository(session_maker)
    booking_repo = SqlAlchemyBookingRepository(session_maker)

    outbox_gateway = build_outbound_gateway(settings, repo=booking_repo)
    assert isinstance(outbox_gateway, StubOutboundGateway)  # ensured by mail_provider == "stub"

    workflow_gateway = TemporalWorkflowGateway(
        client=temporal_client,
        task_queue=settings.temporal_task_queue,
        reply_timeout_seconds=settings.hotel_reply_timeout_seconds,
        followup_max=settings.followup_max_attempts,
        clarify_timeout_seconds=settings.clarify_timeout_seconds,
        reactivation_timeout_seconds=settings.reactivation_timeout_seconds,
        continue_as_new_threshold=settings.workflow_continue_as_new_threshold,
    )
    notifier = EmailClientNotifier(
        gateway=outbox_gateway, clients=clients_repo, mail_domain=settings.mail_domain
    )
    activities = ConciergeActivities(
        extractor=agents.extractor,
        discoverer=agents.discoverer,
        negotiator=agents.negotiator,
        reporter=agents.reporter,
        gateway=outbox_gateway,
        notifier=notifier,
        bookings=booking_repo,
        mail_domain=settings.mail_domain,
    )
    worker = worker if worker is not None else build_worker(temporal_client, settings, activities)

    intake = IntakeService(clients=clients_repo, gateway=workflow_gateway)
    dispatcher = InboundDispatcher(
        clients=clients_repo, bookings=booking_repo, mail_domain=settings.mail_domain
    )
    app = create_app(
        webhook_deps=build_webhook_deps(
            settings=settings,
            normalizer=build_inbound_normalizer(settings),
            dispatcher=dispatcher,
            gateway=workflow_gateway,
            intake=intake,
        )
    )
    _logger.info(
        "local.runtime.assembled",
        mail_provider=settings.mail_provider,
        task_queue=settings.temporal_task_queue,
        temporal_target=settings.temporal_target,
    )
    return LocalRuntime(
        app=app, worker=worker, temporal_client=temporal_client, http_client=client_http,
        outbox_gateway=outbox_gateway,
    )
