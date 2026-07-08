"""SQLAlchemy-backed repositories (Postgres in production; SQLite-compatible for tests)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domain.entities import Booking, Client, Message
from domain.ids import BookingId, ClientToken, MessageId
from infrastructure.db.mappers import (
    booking_from_orm,
    booking_to_orm,
    client_from_orm,
    client_to_orm,
    message_from_orm,
    message_to_orm,
    topic_to_orm,
)
from infrastructure.db.models import BookingORM, ClientORM, MessageORM


def _merge_topics(session: AsyncSession, orm: BookingORM, booking: Booking) -> None:
    """Reconcile the booking's topics onto the ORM relationship (insert/update/remove)."""
    existing = {t.topic_id: t for t in orm.topics}
    seen: set[str] = set()
    for topic in booking.topics:
        seen.add(topic.topic_id)
        if topic.topic_id in existing:
            row = existing[topic.topic_id]
            row.label = topic.label
            row.status = topic.status.value
            row.result = topic.result
        else:
            orm.topics.append(topic_to_orm(topic, booking.booking_id))
    # drop removed topics
    orm.topics = [t for t in orm.topics if t.topic_id in seen]


class SqlAlchemyClientRepository:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def add(self, client: Client) -> None:
        async with self._factory() as session:
            session.add(client_to_orm(client))
            await session.commit()

    async def by_token(self, token: ClientToken) -> Client | None:
        async with self._factory() as session:
            orm = await session.get(ClientORM, token)
            return client_from_orm(orm) if orm else None


class SqlAlchemyBookingRepository:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def get(self, booking_id: BookingId) -> Booking | None:
        async with self._factory() as session:
            orm = await session.get(BookingORM, booking_id)
            if orm is None:
                return None
            return booking_from_orm(orm)

    async def save(self, booking: Booking) -> None:
        async with self._factory() as session:
            orm = await session.get(BookingORM, booking.booking_id)
            if orm is None:
                session.add(booking_to_orm(booking))
            else:
                _apply_booking(orm, booking)
                _merge_topics(session, orm, booking)
            await session.commit()

    async def add_message(self, message: Message) -> MessageId | None:
        """Insert idempotently on ``idempotency_key`` (dedup across activity retries)."""
        async with self._factory() as session:
            orm = message_to_orm(message)
            if message.idempotency_key:
                existing = await session.scalar(
                    select(MessageORM).where(MessageORM.idempotency_key == message.idempotency_key)
                )
                if existing is not None:
                    return None
            session.add(orm)
            try:
                await session.commit()
            except IntegrityError:
                # Concurrent insert with the same unique key → already stored.
                await session.rollback()
                return None
            return message.message_id

    async def messages(self, booking_id: BookingId) -> list[Message]:
        async with self._factory() as session:
            stmt = (
                select(MessageORM)
                .where(MessageORM.booking_id == booking_id)
                .order_by(MessageORM.created_at)
            )
            rows = (await session.scalars(stmt)).all()
            return [message_from_orm(r) for r in rows]


def _apply_booking(orm: BookingORM, booking: Booking) -> None:
    """Copy scalar/relation fields from a domain booking onto an existing ORM row."""
    orm.client_token = booking.client_token
    orm.hotel_name = booking.hotel.hotel_name
    orm.hotel_email = booking.hotel.email.value if booking.hotel.email else None
    orm.hotel_website = booking.hotel.website
    orm.hotel_language = booking.hotel.language
    orm.hotel_discovered = booking.hotel.discovered
    orm.booking_ref = booking.booking_ref
    orm.check_in = booking.check_in
    orm.check_out = booking.check_out
    orm.guests = list(booking.guests)
    orm.room_type = booking.room_type
    orm.language = booking.language
    orm.wishes = list(booking.wishes)
    orm.lifecycle = booking.lifecycle.value
    orm.report = booking.report
    orm.followup_attempts = booking.followup_attempts


__all__ = ["SqlAlchemyBookingRepository", "SqlAlchemyClientRepository"]
