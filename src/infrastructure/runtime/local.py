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
DB session factory); ``main_local.run_local`` connects the real ones and runs worker + API + Telegram
poller in one process. The split keeps the wiring unit-testable without Temporal / LLM / DB.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from aiogram import Bot, Dispatcher
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio.client import Client
from temporalio.worker import Worker

from domain.application import ChatIntakeService, InboundDispatcher, IntakeService, MailboxService
from domain.enums import Channel
from domain.ports import ClientNotifier
from infrastructure.agents.factory import AgentBundle
from infrastructure.agents.surface import SurfaceAgent, SurfaceComponents, SurfaceDeps
from infrastructure.config import Settings
from infrastructure.identity import generate_client_token
from infrastructure.logging import get_logger
from infrastructure.mail.factory import build_inbound_normalizer, build_outbound_gateway
from infrastructure.mail.notifier import (
    CoalescingClientNotifier,
    EmailClientNotifier,
    RoutingClientNotifier,
)
from infrastructure.mail.stub import StubOutboundGateway
from infrastructure.persistence.sqlalchemy_repos import (
    SqlAlchemyBookingRepository,
    SqlAlchemyChannelSessionRepository,
    SqlAlchemyClientRepository,
)
from infrastructure.telegram import (
    AiogramBotPort,
    TelegramAdapter,
    TelegramClientNotifier,
    build_router,
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
    # Telegram surface (inbound adapter). None when no surface agent was provided (bot runs as a
    # separate process per design D10); the API endpoint + outbound notifier still work without it.
    telegram: TelegramAdapter | None = None
    # The aiogram Bot + Dispatcher used to poll Telegram inbound. None when telegram is None.
    # ``run_local`` starts/stops polling on these; the FastAPI app itself does not touch them.
    telegram_bot: Bot | None = None
    telegram_dispatcher: Dispatcher | None = None


def build_local_app(
    settings: Settings,
    *,
    temporal_client: Client,
    agents: AgentBundle,
    session_maker: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient | None = None,
    worker: Worker | None = None,
    surface_components: SurfaceComponents | None = None,
) -> LocalRuntime:
    """Assemble the FastAPI app + Temporal worker with stub mail collaborators.

    Pure and synchronous: caller supplies the already-connected Temporal client, the built agent
    bundle, and a DB session factory. Returns a :class:`LocalRuntime` whose ``worker`` is created but
    not started (``run_local`` starts it). Pass ``worker`` to inject a fake (tests) instead of
    constructing a real :class:`Worker` from ``temporal_client``.

    Pass ``surface_components`` (the LLM model + web backends + checkpointer shared with the other
    agents) to build the surface agent here and wire the Telegram adapter when a bot token is set.
    """
    if settings.mail_provider != "stub":
        # Local mode is stub-only by design; guard against accidental Mailgun wiring locally.
        raise ValueError(
            f"local runtime requires KKR_MAIL_PROVIDER=stub, got {settings.mail_provider!r}"
        )

    client_http = http_client or httpx.AsyncClient()
    clients_repo = SqlAlchemyClientRepository(session_maker)
    booking_repo = SqlAlchemyBookingRepository(session_maker)
    sessions_repo = SqlAlchemyChannelSessionRepository(session_maker)

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

    # Outbound notifier: route to the client's channel (Telegram if they have a chat session, else
    # email), coalesced to avoid flooding (design D7). When a Telegram bot token is configured, the
    # worker pushes progress to the chat directly via the Bot API.
    email_notifier = EmailClientNotifier(
        gateway=outbox_gateway, clients=clients_repo, mail_domain=settings.mail_domain
    )
    channels: dict[Channel, ClientNotifier] = {}
    # The aiogram Bot for both inbound polling and outbound sends; wrapped in AiogramBotPort for the
    # adapter/notifier so they stay unit-testable with a recording fake. None when no token is set.
    telegram_bot: Bot | None = (
        Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None
    )
    telegram_bot_port = AiogramBotPort(telegram_bot) if telegram_bot is not None else None
    if telegram_bot_port is not None:
        channels[Channel.TELEGRAM] = TelegramClientNotifier(
            bot=telegram_bot_port, sessions=sessions_repo
        )
    notifier: ClientNotifier = CoalescingClientNotifier(
        inner=RoutingClientNotifier(
            sessions=sessions_repo, email=email_notifier, channels=channels
        )
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

    mailbox = MailboxService(
        clients=clients_repo,
        sessions=sessions_repo,
        mail_domain=settings.mail_domain,
        token_factory=generate_client_token,
    )
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
            mailbox=mailbox,
        )
    )
    # Expose the stub outbox for local inspection (GET /_local/outbox). Production has no outbox.
    app.state.outbox_gateway = outbox_gateway

    # Telegram inbound surface (optional; the bot may run as a separate process, design D10).
    telegram: TelegramAdapter | None = None
    telegram_dispatcher: Dispatcher | None = None
    if surface_components is not None and telegram_bot_port is not None:
        chat_intake = ChatIntakeService(
            sessions=sessions_repo, clients=clients_repo, gateway=workflow_gateway
        )
        surface_agent = SurfaceAgent(
            model=surface_components.model,
            searcher=surface_components.searcher,
            fetcher=surface_components.fetcher,
            checkpointer=surface_components.checkpointer,
            langfuse_callbacks=surface_components.langfuse_callbacks,
            deps=SurfaceDeps(
                mailbox=mailbox,
                sessions=sessions_repo,
                bookings=booking_repo,
                intake=chat_intake,
            ),
        )
        telegram = TelegramAdapter(
            bot=telegram_bot_port, agent=surface_agent, sessions=sessions_repo, mailbox=mailbox
        )
        # aiogram dispatcher: routes /start + messages to the adapter via DI (surface_adapter kwarg).
        telegram_dispatcher = Dispatcher()
        telegram_dispatcher.include_router(build_router())

    _logger.info(
        "local.runtime.assembled",
        mail_provider=settings.mail_provider,
        task_queue=settings.temporal_task_queue,
        temporal_target=settings.temporal_target,
        telegram_surface=telegram is not None,
    )
    return LocalRuntime(
        app=app,
        worker=worker,
        temporal_client=temporal_client,
        http_client=client_http,
        outbox_gateway=outbox_gateway,
        telegram=telegram,
        telegram_bot=telegram_bot,
        telegram_dispatcher=telegram_dispatcher,
    )
