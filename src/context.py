from dataclasses import dataclass
from typing import Annotated

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

__all__ = [
    "AppContext",
    "ApplicationContext",
    "get_context",
    "set_context",
]


@dataclass
class ApplicationContext:
    bot: Bot
    mailtrap_client: MailtrapClient
    session_factory: async_sessionmaker[AsyncSession]
    tavily_client: TavilyClient


_ctx: ApplicationContext | None = None


def get_context() -> ApplicationContext:
    if _ctx is None:
        raise RuntimeError("Application context is not set")
    return _ctx


def set_context(context: ApplicationContext) -> None:
    global _ctx
    _ctx = context


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
