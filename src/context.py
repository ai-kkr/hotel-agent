from dataclasses import dataclass
from typing import Annotated, Any

import fastapi
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tavily.tavily import TavilyClient

from src.config import Settings, get_settings
from src.db.session import create_engine, session_factory
from src.integrations.mailtrap.client import MailtrapClient
from src.integrations.mailtrap.mailtrap_inbound import AuthenticatedClient
from src.llm import build_model

__all__ = [
    "AppContext",
    "ApplicationContext",
    "get_context",
    "init_graph",
    "set_context",
]


@dataclass
class ApplicationContext:
    bot: Bot
    mailtrap_client: MailtrapClient
    session_factory: async_sessionmaker[AsyncSession]
    model: BaseChatModel
    tavily_client: TavilyClient
    # Async Postgres pool backing the LangGraph checkpointer. Created sync (open=False) in
    # ``build_context``; opened in the lifespan.
    checkpoint_pool: AsyncConnectionPool[Any]
    # The saver + the compiled graph are built async in :func:`init_graph` (run inside the app's
    # event loop) because ``AsyncPostgresSaver`` binds to the running loop on construction. They are
    # ``None`` until startup completes; :func:`get_email_graph` asserts readiness at use sites.
    checkpoint_saver: AsyncPostgresSaver | None = None
    email_graph: CompiledStateGraph | None = None

    def email_graph_or_raise(self) -> CompiledStateGraph:
        """Return the compiled agent graph, raising if startup hasn't finished yet."""
        if self.email_graph is None:
            raise RuntimeError("Agent graph is not initialized — was init_graph() called?")
        return self.email_graph


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

    Constructs everything that doesn't need a running event loop. The checkpointer saver and the
    agent graph are wired up by :func:`init_graph` inside the app lifespan, because
    ``AsyncPostgresSaver`` captures the running loop on construction.
    """
    settings = settings or get_settings()
    # Initialize Langfuse tracing (no-op unless KKR_LANGFUSE_ENABLED + keys are set) before the
    # agent runs, so the per-turn CallbackHandler picks up the configured singleton.
    from src.agent.tracing import init_langfuse

    init_langfuse(settings)
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
    # LangGraph checkpointer pool, opened later in the lifespan. ``open=False`` because this runs
    # outside any event loop; the schema (checkpoint_* tables) is applied by ``setup()`` in
    # ``init_graph`` — those tables are langgraph-owned, not part of alembic.
    checkpoint_pool = AsyncConnectionPool(conninfo=settings.langgraph_dsn, open=False)
    ctx = ApplicationContext(
        bot=bot,
        mailtrap_client=mailtrap_client,
        session_factory=session_factory(engine),
        model=build_model(settings=settings),
        tavily_client=TavilyClient(
            api_key=settings.tavily_api_key,
        ),
        checkpoint_pool=checkpoint_pool,
    )
    set_context(ctx)
    return ctx


async def init_graph(ctx: ApplicationContext) -> None:
    """Open the checkpointer pool, apply langgraph's schema, and compile the agent graph.

    Must run inside the app's event loop (uvicorn's): ``AsyncPostgresSaver`` captures the running
    loop on construction, so it cannot be built in the sync :func:`build_context`. The checkpoint_*
    tables are created via ``setup()`` (langgraph's own migrations), not alembic.
    """
    await ctx.checkpoint_pool.open()
    ctx.checkpoint_saver = AsyncPostgresSaver(conn=ctx.checkpoint_pool)
    await ctx.checkpoint_saver.setup()
    # Imported lazily to break the ``context ↔ agent`` import cycle (agent tools fetch their
    # dependencies via get_context() at call time, not import time).
    from src.agent import build_email_agent

    ctx.email_graph = build_email_agent(model=ctx.model, checkpointer=ctx.checkpoint_saver)
