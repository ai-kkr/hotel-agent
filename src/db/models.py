from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.agent.state import EmailState
from src.integrations.mailtrap.mailtrap_inbound.models import MessageDetails

from .base import Base
from .types import MessageDetailsType, StateType


class ClientORM(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int | None] = mapped_column(
        default=None,
        nullable=True,
        unique=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        unique=True,
        index=True,
    )
    inbox_id: Mapped[int] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
    )
    inbox: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        unique=True,
        index=True,
    )

    @property
    def thread_id(self) -> str:
        """Return a thread ID for this client.

        The thread ID is used to group related emails together in the agent workflow.
        For now, we use the inbox ID as the thread ID, but this can be changed in the future
        if we want to implement more sophisticated threading logic.
        """
        return f"client:{self.id:04d}"


class ForwardedEmailORM(Base):
    __tablename__ = "forwarded_emails"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data: Mapped[MessageDetails] = mapped_column(MessageDetailsType)

    @property
    def thread_id(self) -> str:
        """Return a thread ID for this forwarded email.

        The thread ID is used to group related emails together in the agent workflow.
        For now, we use the message ID as the thread ID, but this can be changed in the future
        if we want to implement more sophisticated threading logic.
        """
        return f"email:{self.client_id:04d}:{self.id}"


class OutboundEmailORM(Base):
    """An email the agent sent to a hotel (the initial letter or a reply).

    Persisted so the inbound webhook can match a hotel's reply by its ``In-Reply-To`` header
    (which carries the ``message_id`` of the outbound email we sent) and route it back to the
    agent as a ``hotel reply:`` turn.
    """

    __tablename__ = "outbound_emails"
    message_id: Mapped[str] = mapped_column(String(320), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class StateORM(Base):
    """Persisted agent state for a client.

    One row per client (``client_id`` is the primary key). The ``state`` column holds the
    serialized :class:`EmailState` as native JSON — ``JSONB`` on Postgres (binary, indexable, no
    duplicate keys), falling back to plain ``JSON`` on SQLite (tests). ``created_at``/``updated_at``
    track when the row was first written and last refreshed.
    """

    __tablename__ = "states"
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    client: Mapped[ClientORM] = relationship("ClientORM", backref="state", uselist=False)
    state: Mapped[EmailState] = mapped_column(
        StateType,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


class ScheduledTaskORM(Base):
    """DB catalog row for a client's scheduled task — the index the agent lists/checks cheaply.

    Temporal Schedules can't be filtered server-side when listing (no search-attribute / id list
    filter — the visibility list filter only applies to Workflow Executions), so a per-client scan of
    all schedules is the only Temporal-side option. To avoid that on every list / update / cancel, we
    keep our own per-client index of ``task_key`` + the display metadata ``list_scheduled_tasks``
    renders. Temporal remains the source of truth for the actual firing (cron/timing/action); this
    table is the source of truth for "which tasks a client has" and what to show. Kept in sync on
    every create / update / cancel (see :mod:`src.agent.tools.scheduling` for the write ordering);
    a crash between the Temporal write and this one is a rare divergence temporal-ui can reconcile.
    """

    __tablename__ = "scheduled_tasks"
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    task_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    spec_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: For a bounded recurring task (``cron`` + ``remaining``) — the remaining-firings count shown in
    #: the listing. ``None`` for one-shot / unbounded recurring (then "осталось N" is not rendered).
    remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
