"""Alembic environment.

Runs migrations against the async Postgres DSN from :class:`Settings`. The metadata target is
``src.db.base.Base.metadata`` (importing ``src.db.models`` registers models).

Only tables present in the metadata are managed: objects that exist in the DB but are absent
from the target metadata (legacy v1 tables like ``bookings``/``messages``) are ignored rather
than dropped, so autogenerate never emits destructive drops for unmanaged tables.
"""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Repo root is not on sys.path by default (alembic.ini prepends ``.``); add it so the ``src``
# package is importable.
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import src.db.models  # noqa: E402,F401  (registers all ORM models on Base)
from src.config import get_settings  # noqa: E402
from src.db.base import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_url() -> str:
    return get_settings().postgres_dsn


def _include_object(object_, name, type_, reflected, compare_to):
    """Manage only objects described by the v2 metadata.

    A reflected object with no counterpart in the metadata (``compare_to is None``) is a legacy
    v1 object we no longer model — leave it untouched instead of generating a drop.
    """
    if reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(
        _resolve_url(),
        poolclass=pool.NullPool,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
