from __future__ import annotations

from datetime import UTC, datetime

import pytest_asyncio

from domain.application import InboundDispatcher
from domain.entities import Booking, Client, HotelContact
from domain.events import ClientMessage, ConfirmForward, HotelReply, InboundEmail
from domain.ids import EmailAddress
from infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryClientRepository,
)


@pytest_asyncio.fixture
async def dispatcher() -> InboundDispatcher:
    clients = InMemoryClientRepository()
    bookings = InMemoryBookingRepository()
    await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
    await bookings.save(
        Booking.start(
            booking_id="b1",
            client_token="tok",
            hotel=HotelContact(hotel_name="Grand", email=EmailAddress("hotel@grand.com")),
        )
    )
    return InboundDispatcher(clients=clients, bookings=bookings, mail_domain="kkr-hotel.com")


def _email(recipient: str, sender: str) -> InboundEmail:
    return InboundEmail(
        recipients=[recipient],
        sender=EmailAddress(sender),
        subject="Re: booking",
        body="hello",
        received_at=datetime.now(tz=UTC),
    )


async def test_intake_routes_to_confirm_forward(dispatcher: InboundDispatcher) -> None:
    events = await dispatcher.dispatch(_email("c.tok@kkr-hotel.com", "client@example.com"))
    assert len(events) == 1
    assert isinstance(events[0], ConfirmForward)
    assert events[0].client_token == "tok"


async def test_conversation_from_hotel_is_hotel_reply(dispatcher: InboundDispatcher) -> None:
    events = await dispatcher.dispatch(_email("b.b1@kkr-hotel.com", "hotel@grand.com"))
    assert len(events) == 1
    assert isinstance(events[0], HotelReply)
    assert events[0].booking_id == "b1"


async def test_conversation_from_client_is_client_message(dispatcher: InboundDispatcher) -> None:
    events = await dispatcher.dispatch(_email("b.b1@kkr-hotel.com", "client@example.com"))
    assert len(events) == 1
    assert isinstance(events[0], ClientMessage)
    assert events[0].booking_id == "b1"


async def test_unknown_booking_conversation_ignored(dispatcher: InboundDispatcher) -> None:
    events = await dispatcher.dispatch(_email("b.999@kkr-hotel.com", "x@y.com"))
    assert events == []


async def test_non_domain_recipient_ignored(dispatcher: InboundDispatcher) -> None:
    events = await dispatcher.dispatch(_email("c.tok@other.com", "client@example.com"))
    assert events == []


async def test_multiple_recipients_dispatch_each(dispatcher: InboundDispatcher) -> None:
    email = InboundEmail(
        recipients=["b.b1@kkr-hotel.com", "c.tok@kkr-hotel.com"],
        sender=EmailAddress("client@example.com"),
        subject="s",
        body="b",
        received_at=datetime.now(tz=UTC),
    )
    events = await dispatcher.dispatch(email)
    assert len(events) == 2


async def test_unknown_local_part_ignored(dispatcher: InboundDispatcher) -> None:
    events = await dispatcher.dispatch(_email("random@kkr-hotel.com", "x@y.com"))
    assert events == []
