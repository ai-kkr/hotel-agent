"""Async SQLAlchemy engine / session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.db.base import Base


def create_engine(
    dsn: str,
    *,
    pool_pre_ping: bool = True,
    pool_recycle: int = 1800,
    **engine_kwargs: Any,
) -> AsyncEngine:
    """Create the async engine with asyncpg-safe pool defaults.

    Stale-connection guard: asyncpg sockets in the pool can be closed by the server / OS while
    idle, and without a checkout check the next request fails on BEGIN with
    ``ConnectionDoesNotExistError``. ``pool_pre_ping`` checks at checkout; ``pool_recycle``
    retires them proactively.
    """
    return create_async_engine(
        dsn,
        future=True,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        **engine_kwargs,
    )


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine) -> None:
    """Create all tables (used in tests; production uses Alembic migrations)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
        await session.commit()


session_context = asynccontextmanager(session_scope)
