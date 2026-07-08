"""Mapping between ORM models and domain entities."""

from __future__ import annotations

from domain.entities import Booking, Client, HotelContact, Message, Topic
from domain.enums import BookingLifecycle, Channel, MessageDirection, SenderRole, TopicStatus
from domain.ids import EmailAddress
from infrastructure.db.models import BookingORM, ClientORM, MessageORM, TopicORM


def _email(value: str | None) -> EmailAddress | None:
    return EmailAddress(value) if value else None


# --- Client ---


def client_to_orm(client: Client) -> ClientORM:
    return ClientORM(token=client.token, email=client.email.value, name=client.name)


def client_from_orm(orm: ClientORM) -> Client:
    return Client(token=orm.token, email=EmailAddress(orm.email), name=orm.name)


# --- Topic ---


def topic_to_orm(topic: Topic, booking_id: str) -> TopicORM:
    return TopicORM(
        booking_id=booking_id,
        topic_id=topic.topic_id,
        label=topic.label,
        status=topic.status.value,
        result=topic.result,
    )


def topic_from_orm(orm: TopicORM) -> Topic:
    return Topic(
        topic_id=orm.topic_id,
        label=orm.label,
        status=TopicStatus(orm.status),
        result=orm.result,
    )


# --- Booking ---


def booking_to_orm(booking: Booking) -> BookingORM:
    return BookingORM(
        booking_id=booking.booking_id,
        client_token=booking.client_token,
        hotel_name=booking.hotel.hotel_name,
        hotel_email=booking.hotel.email.value if booking.hotel.email else None,
        hotel_website=booking.hotel.website,
        hotel_language=booking.hotel.language,
        hotel_discovered=booking.hotel.discovered,
        booking_ref=booking.booking_ref,
        check_in=booking.check_in,
        check_out=booking.check_out,
        guests=list(booking.guests),
        room_type=booking.room_type,
        language=booking.language,
        wishes=list(booking.wishes),
        lifecycle=booking.lifecycle.value,
        report=booking.report,
        followup_attempts=booking.followup_attempts,
        topics=[topic_to_orm(t, booking.booking_id) for t in booking.topics],
    )


def booking_from_orm(orm: BookingORM) -> Booking:
    hotel = HotelContact(
        hotel_name=orm.hotel_name,
        email=_email(orm.hotel_email),
        website=orm.hotel_website,
        language=orm.hotel_language,
        discovered=orm.hotel_discovered,
    )
    booking = Booking(
        booking_id=orm.booking_id,
        client_token=orm.client_token,
        hotel=hotel,
        booking_ref=orm.booking_ref,
        check_in=orm.check_in,
        check_out=orm.check_out,
        guests=list(orm.guests or []),
        room_type=orm.room_type,
        language=orm.language,
        wishes=list(orm.wishes or []),
        lifecycle=BookingLifecycle(orm.lifecycle),
        report=orm.report,
        followup_attempts=orm.followup_attempts,
    )
    booking.topics = [topic_from_orm(t) for t in orm.topics]
    return booking


# --- Message ---


def message_to_orm(message: Message) -> MessageORM:
    return MessageORM(
        message_id=message.message_id,
        booking_id=message.booking_id,
        direction=message.direction.value,
        channel=message.channel.value,
        sender=message.sender.value if message.sender else None,
        recipient=message.recipient.value if message.recipient else None,
        subject=message.subject,
        body=message.body,
        sender_role=message.sender_role.value,
        idempotency_key=message.idempotency_key,
        created_at=message.created_at,
    )


def message_from_orm(orm: MessageORM) -> Message:
    return Message(
        message_id=orm.message_id,
        booking_id=orm.booking_id,
        direction=MessageDirection(orm.direction),
        channel=Channel(orm.channel),
        sender=_email(orm.sender),
        recipient=_email(orm.recipient),
        subject=orm.subject,
        body=orm.body,
        sender_role=SenderRole(orm.sender_role),
        idempotency_key=orm.idempotency_key,
        created_at=orm.created_at,
    )
