from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

import fastapi
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tavily.tavily import TavilyClient

from src.config import Settings, get_settings
from src.db.session import create_engine, session_factory
from src.integrations.mailtrap.client import MailtrapClient
from src.integrations.mailtrap.mailtrap_inbound import AuthenticatedClient

if TYPE_CHECKING:
    from temporalio.client import Client

__all__ = [
    "AppContext",
    "ApplicationContext",
    "get_context",
    "get_temporal_client",
    "set_context",
]


@dataclass
class ApplicationContext:
    bot: Bot
    mailtrap_client: MailtrapClient
    session_factory: async_sessionmaker[AsyncSession]
    tavily_client: TavilyClient
    #: Lazily-connected Temporal client (one per worker process), reused by the scheduling tools
    #: and the ``enqueue_scheduled_turn`` activity. Connected on first access via
    #: :func:`get_temporal_client`; ``None`` until then.
    temporal_client: Client | None = None


_ctx: ApplicationContext | None = None

#: Serialises the lazy ``Client.connect`` in :func:`get_temporal_client` so two concurrent
#: first-callers don't both connect (the loser's client would be orphaned — a connection leak).
#: Binds to the running loop on first use (Python 3.10+ ``asyncio.Lock`` needs no loop at creation).
_temporal_client_lock = asyncio.Lock()


def get_context() -> ApplicationContext:
    if _ctx is None:
        raise RuntimeError("Application context is not set")
    return _ctx


def set_context(context: ApplicationContext) -> None:
    global _ctx
    _ctx = context


async def get_temporal_client() -> Client:
    """Return the process-wide Temporal client, connecting it lazily on first use.

    Scheduling tools and the ``enqueue_scheduled_turn`` activity reach the Temporal Schedule API
    through this instead of a per-call ``Client.connect`` (which is what the HTTP-handler-driven
    ``agent_step`` path does). Uses the same ``message_aware_data_converter`` as the worker so the
    ``RunInput`` frozen into a Schedule action round-trips identically to ``agent_step``.

    Double-checked under :data:`_temporal_client_lock`: the connect is an ``await``, so without the
    lock two concurrent first-callers would both connect and the loser's client would be leaked.
    """
    ctx = get_context()
    if ctx.temporal_client is not None:
        return ctx.temporal_client
    async with _temporal_client_lock:
        if ctx.temporal_client is not None:  # re-check — another task may have connected while we waited
            return ctx.temporal_client
        # Imported lazily so importing this module (pulled in broadly by the FastAPI app) never
        # imports temporalio at load time.
        from temporalio.client import Client

        from src.temporal.converter import message_aware_data_converter

        settings = get_settings()
        ctx.temporal_client = await Client.connect(
            settings.temporal_target,
            data_converter=message_aware_data_converter,
        )
    return ctx.temporal_client


type AppContext = Annotated[ApplicationContext, fastapi.Depends(get_context)]


def build_context(settings: Settings | None = None) -> ApplicationContext:
    """Build the application context (sync).

    Constructs everything that doesn't need a running event loop. Langfuse tracing is initialised
    later (in the Temporal worker lifespan) before the agent runs.
    """
    settings = settings or get_settings()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )
    mailtrap_client = MailtrapClient(
        AuthenticatedClient(
            base_url=settings.mailtrap_base_url,
            token=settings.mailtrap_api_key,
        )
    )
    engine = create_engine(dsn=settings.postgres_dsn)
    ctx = ApplicationContext(
        bot=bot,
        mailtrap_client=mailtrap_client,
        session_factory=session_factory(engine),
        tavily_client=TavilyClient(
            api_key=settings.tavily_api_key,
        ),
    )
    set_context(ctx)
    return ctx
