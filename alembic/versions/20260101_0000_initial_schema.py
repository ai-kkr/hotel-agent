"""initial schema: clients, bookings, topics, messages

Revision ID: 0000_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0000_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("token"),
        sa.UniqueConstraint("email", name="uq_clients_email"),
    )

    op.create_table(
        "bookings",
        sa.Column("booking_id", sa.String(length=64), nullable=False),
        sa.Column("client_token", sa.String(length=64), nullable=False),
        sa.Column("hotel_name", sa.String(length=512), nullable=False),
        sa.Column("hotel_email", sa.String(length=320), nullable=True),
        sa.Column("hotel_website", sa.String(length=1024), nullable=True),
        sa.Column("hotel_language", sa.String(length=8), nullable=True),
        sa.Column("hotel_discovered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("booking_ref", sa.String(length=128), nullable=True),
        sa.Column("check_in", sa.Date(), nullable=True),
        sa.Column("check_out", sa.Date(), nullable=True),
        sa.Column("guests", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("room_type", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("wishes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("lifecycle", sa.String(length=64), nullable=False, server_default="intake"),
        sa.Column("report", sa.Text(), nullable=True),
        sa.Column("followup_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_token"], ["clients.token"]),
        sa.PrimaryKeyConstraint("booking_id"),
    )
    op.create_index("ix_bookings_client_token", "bookings", ["client_token"])

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("booking_id", sa.String(length=64), nullable=False),
        sa.Column("topic_id", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.booking_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", "topic_id", name="uq_topics_booking_topic"),
    )

    op.create_table(
        "messages",
        sa.Column("message_id", sa.String(length=128), nullable=False),
        sa.Column("booking_id", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("sender", sa.String(length=320), nullable=True),
        sa.Column("recipient", sa.String(length=320), nullable=True),
        sa.Column("subject", sa.String(length=512), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sender_role", sa.String(length=16), nullable=False, server_default="system"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.booking_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("message_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_messages_idempotency_key"),
    )
    op.create_index("ix_messages_booking_id", "messages", ["booking_id"])
    op.create_index("ix_messages_booking_created", "messages", ["booking_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_messages_booking_created", table_name="messages")
    op.drop_index("ix_messages_booking_id", table_name="messages")
    op.drop_table("messages")
    op.drop_table("topics")
    op.drop_index("ix_bookings_client_token", table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("clients")
