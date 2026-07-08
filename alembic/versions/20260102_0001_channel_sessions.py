"""add channel_sessions table (additive; CANCELLED lifecycle is text-stored)

Revision ID: 0001_channel_sessions
Revises: 0000_initial
Create Date: 2026-01-02 00:00:00

Adds the per-client channel-session binding (e.g. Telegram ``chat_id``) for the Telegram surface
(design D5 / client-communication spec). Additive only: the existing email channel is untouched, and
``BookingLifecycle.CANCELLED`` needs no column change because ``lifecycle`` is stored as free text.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_channel_sessions"
down_revision: str | None = "0000_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channel_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_token", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_token"], ["clients.token"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel", "address", name="uq_channel_sessions_channel_address"),
    )
    op.create_index("ix_channel_sessions_client_token", "channel_sessions", ["client_token"])


def downgrade() -> None:
    op.drop_index("ix_channel_sessions_client_token", table_name="channel_sessions")
    op.drop_table("channel_sessions")
