"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import infrastructure.db.models  # noqa: F401
from infrastructure.db.base import Base


@pytest.fixture
def now() -> datetime:
    return datetime.now(tz=UTC)


@pytest_asyncio.fixture
async def sqlite_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def sqlite_factory(sqlite_engine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield async_sessionmaker(sqlite_engine, expire_on_commit=False)
