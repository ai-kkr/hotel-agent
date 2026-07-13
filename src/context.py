from dataclasses import dataclass
from typing import Annotated

import fastapi
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tavily.tavily import TavilyClient

from src.agent import build_email_agent
from src.config import get_settings
from src.db.session import create_engine, session_factory
from src.integrations.mailtrap.client import MailtrapClient
from src.integrations.mailtrap.mailtrap_inbound import AuthenticatedClient
from src.llm import build_model

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
    model: BaseChatModel
    tavily_client: TavilyClient
    email_graph: CompiledStateGraph


_ctx: ApplicationContext | None = None


def get_context() -> ApplicationContext:
    if _ctx is None:
        raise RuntimeError("Application context is not set")
    return _ctx


def set_context(context: ApplicationContext) -> None:
    global _ctx
    _ctx = context


type AppContext = Annotated[ApplicationContext, fastapi.Depends(get_context)]


def build_context() -> ApplicationContext:
    settings = get_settings()
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
    checkpointer = MemorySaver()
    ctx = ApplicationContext(
        bot=bot,
        mailtrap_client=mailtrap_client,
        session_factory=session_factory(engine),
        model=build_model(settings=settings),
        tavily_client=TavilyClient(
            api_key=settings.tavily_api_key,
        ),
        email_graph=build_email_agent(
            model=build_model(settings=settings),
            checkpointer=checkpointer,
        ),
    )
    set_context(ctx)
    return ctx
