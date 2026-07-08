"""SQLAlchemy ORM models for the domain aggregates.

Models are storage-oriented; the domain layer never imports them. Mapping lives in
``infrastructure.db.mappers``.

List/dict fields use a JSON type that is ``JSONB`` on PostgreSQL and ``JSON`` elsewhere, so the same
code runs against in-process SQLite in tests and Postgres in production.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base

# JSONB on Postgres, JSON elsewhere (e.g. SQLite in tests).
DialectJSON = JSON().with_variant(JSONB(), "postgresql")


def _now() -> datetime:
    return datetime.now(tz=UTC)


class ClientORM(Base):
    __tablename__ = "clients"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    bookings: Mapped[list[BookingORM]] = relationship(back_populates="client")


class BookingORM(Base):
    __tablename__ = "bookings"

    booking_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_token: Mapped[str] = mapped_column(ForeignKey("clients.token"), nullable=False, index=True)

    # hotel contact
    hotel_name: Mapped[str] = mapped_column(String(512), nullable=False)
    hotel_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    hotel_website: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    hotel_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    hotel_discovered: Mapped[bool] = mapped_column(default=False, nullable=False)

    # extracted fields
    booking_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    check_in: Mapped[date | None] = mapped_column(nullable=True)
    check_out: Mapped[date | None] = mapped_column(nullable=True)
    guests: Mapped[list[str]] = mapped_column(DialectJSON, nullable=False, default=list)
    room_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # negotiation state
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    wishes: Mapped[list[str]] = mapped_column(DialectJSON, nullable=False, default=list)
    lifecycle: Mapped[str] = mapped_column(String(64), nullable=False, default="intake")
    report: Mapped[str | None] = mapped_column(Text, nullable=True)
    followup_attempts: Mapped[int] = mapped_column(default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    client: Mapped[ClientORM] = relationship(back_populates="bookings")
    topics: Mapped[list[TopicORM]] = relationship(
        back_populates="booking", cascade="all, delete-orphan", lazy="selectin"
    )


class TopicORM(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    booking: Mapped[BookingORM] = relationship(back_populates="topics")

    __table_args__ = (UniqueConstraint("booking_id", "topic_id", name="uq_topics_booking_topic"),)


class MessageORM(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    sender: Mapped[str | None] = mapped_column(String(320), nullable=True)
    recipient: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sender_role: Mapped[str] = mapped_column(String(16), nullable=False, default="system")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (Index("ix_messages_booking_created", "booking_id", "created_at"),)


class ChannelSessionORM(Base):
    """A client ↔ channel-address binding (e.g. Telegram ``chat_id``).

    Additive over the email-only core (design D5 / client-communication spec). Rollback = drop table.
    """

    __tablename__ = "channel_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_token: Mapped[str] = mapped_column(ForeignKey("clients.token"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    client: Mapped[ClientORM] = relationship()

    __table_args__ = (
        UniqueConstraint("channel", "address", name="uq_channel_sessions_channel_address"),
    )
