"""add states

Revision ID: 7c8d9e0f1a2b
Revises: a1b2c3d4e5f6
Create Date: 2026-07-17 14:30:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7c8d9e0f1a2b"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "states",
        sa.Column("client_id", sa.Integer(), nullable=False),
        # Native JSON: JSONB on Postgres, JSON on SQLite (tests). JSONB is binary/indexable and
        # collapses duplicate keys; the variant keeps the test DB on SQLite working.
        sa.Column(
            "state",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("client_id"),
    )


def downgrade() -> None:
    op.drop_table("states")
