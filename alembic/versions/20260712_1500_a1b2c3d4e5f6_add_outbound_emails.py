"""add outbound_emails

Revision ID: a1b2c3d4e5f6
Revises: f5d614d8fceb
Create Date: 2026-07-12 15:00:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f5d614d8fceb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbound_emails",
        sa.Column("message_id", sa.String(length=320), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=1024), nullable=True),
        sa.Column("in_reply_to", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_index(
        op.f("ix_outbound_emails_client_id"), "outbound_emails", ["client_id"], unique=False
    )
    op.create_index(
        op.f("ix_outbound_emails_in_reply_to"),
        "outbound_emails",
        ["in_reply_to"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_outbound_emails_in_reply_to"), table_name="outbound_emails")
    op.drop_index(op.f("ix_outbound_emails_client_id"), table_name="outbound_emails")
    op.drop_table("outbound_emails")
