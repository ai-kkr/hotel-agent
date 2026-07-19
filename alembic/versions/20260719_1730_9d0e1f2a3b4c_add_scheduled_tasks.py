"""add scheduled_tasks index

Revision ID: 9d0e1f2a3b4c
Revises: 7c8d9e0f1a2b
Create Date: 2026-07-19 17:30:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d0e1f2a3b4c"
down_revision: str | None = "7c8d9e0f1a2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Per-client catalog of scheduled tasks (the agent's cheap list/existence index). Temporal
    # Schedules can't be filtered server-side, so we index task_key + display metadata ourselves.
    # The composite primary key (client_id, task_key) also serves client_id-prefix lookups.
    op.create_table(
        "scheduled_tasks",
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("task_key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=False),
        sa.Column("spec_summary", sa.String(length=255), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("remaining", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("client_id", "task_key"),
    )


def downgrade() -> None:
    op.drop_table("scheduled_tasks")
