from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from domain.entities import Booking, Client, HotelContact, Message
from domain.enums import Channel, MessageDirection, SenderRole, TopicStatus
from domain.ids import BookingId, EmailAddress
from infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryClientRepository,
)
from infrastructure.persistence.sqlalchemy_repos import (
    SqlAlchemyBookingRepository,
    SqlAlchemyClientRepository,
)


def _client() -> Client:
    return Client(token="tok", email=EmailAddress("c@x.com"), name="Alice")


def _booking() -> Booking:
    b = Booking.start(
        booking_id="b1",
        client_token="tok",
        hotel=HotelContact(hotel_name="Grand", email=EmailAddress("h@grand.com")),
        language="fr",
    )
    b.booking_ref = "REF1"
    b.check_in = date(2026, 2, 1)
    b.check_out = date(2026, 2, 4)
    b.guests = ["Alice"]
    b.add_wish("high floor")
    b.add_topic("late-checkout")
    return b


def _message(booking_id: BookingId, idem: str | None = "k1") -> Message:
    return Message(
        message_id="m1",
        booking_id=booking_id,
        direction=MessageDirection.OUTBOUND,
        channel=Channel.EMAIL,
        body="hello hotel",
        created_at=datetime.now(tz=UTC),
        sender=EmailAddress("b1@kkr-hotel.com"),
        recipient=EmailAddress("h@grand.com"),
        sender_role=SenderRole.SYSTEM,
        idempotency_key=idem,
    )


def _assert_booking_roundtrip(b: Booking) -> None:
    assert b.booking_id == "b1"
    assert b.language == "fr"
    assert b.hotel.email is not None and b.hotel.email.value == "h@grand.com"
    assert {t.label for t in b.topics} == {"early-checkin", "room-upgrade", "late-checkout"}
    assert b.wishes == ["high floor"]
    assert b.guests == ["Alice"]


@pytest.mark.parametrize(
    "factory",
    ["inmemory", "sqlalchemy"],
    indirect=True,
)
async def test_save_and_get_booking_roundtrip(factory) -> None:  # type: ignore[no-untyped-def]
    repo, _clients = factory
    await repo.save(_booking())
    loaded = await repo.get("b1")
    assert loaded is not None
    _assert_booking_roundtrip(loaded)


@pytest.mark.parametrize("factory", ["inmemory", "sqlalchemy"], indirect=True)
async def test_save_updates_existing_booking(factory) -> None:  # type: ignore[no-untyped-def]
    repo, _ = factory
    booking = _booking()
    await repo.save(booking)
    booking.topic("b1:t:early-checkin").resolve("granted")
    booking.followup_attempts = 2
    await repo.save(booking)

    loaded = await repo.get("b1")
    assert loaded is not None
    assert loaded.topic("b1:t:early-checkin").status is TopicStatus.RESOLVED
    assert loaded.topic("b1:t:early-checkin").result == "granted"
    assert loaded.followup_attempts == 2


@pytest.mark.parametrize("factory", ["inmemory", "sqlalchemy"], indirect=True)
async def test_message_idempotency_on_retry(factory) -> None:  # type: ignore[no-untyped-def]
    repo, _ = factory
    first = await repo.add_message(_message("b1", idem="b1:initial"))
    second = await repo.add_message(_message("b1", idem="b1:initial"))
    assert first == "m1"
    assert second is None  # deduped
    msgs = await repo.messages("b1")
    assert len(msgs) == 1


@pytest.mark.parametrize("factory", ["inmemory", "sqlalchemy"], indirect=True)
async def test_messages_ordered(factory) -> None:  # type: ignore[no-untyped-def]
    repo, _ = factory
    t = datetime.now(tz=UTC)
    await repo.save(_booking())
    await repo.add_message(
        Message(
            message_id="m1",
            booking_id="b1",
            direction=MessageDirection.INBOUND,
            channel=Channel.EMAIL,
            body="first",
            created_at=t,
        )
    )
    from datetime import timedelta

    await repo.add_message(
        Message(
            message_id="m2",
            booking_id="b1",
            direction=MessageDirection.INBOUND,
            channel=Channel.EMAIL,
            body="second",
            created_at=t + timedelta(seconds=5),
        )
    )
    msgs = await repo.messages("b1")
    assert [m.body for m in msgs] == ["first", "second"]


@pytest.mark.parametrize("factory", ["inmemory", "sqlalchemy"], indirect=True)
async def test_client_lookup(factory) -> None:  # type: ignore[no-untyped-def]
    _, client_repo = factory
    await client_repo.add(_client())
    found = await client_repo.by_token("tok")
    assert found is not None and found.email.value == "c@x.com"
    assert await client_repo.by_token("unknown") is None


# --- factory fixture returning both repo implementations ---------------------------


@pytest.fixture
def factory(request):  # type: ignore[no-untyped-def]
    kind = request.param
    if kind == "inmemory":
        client_repo = InMemoryClientRepository()
        booking_repo = InMemoryBookingRepository()
        return booking_repo, client_repo

    # sqlalchemy: built per-test against the shared sqlite session factory
    request.getfixturevalue("sqlite_factory")
    return request.getfixturevalue("_sqla_repos")


@pytest.fixture
def _sqla_repos(sqlite_factory):  # type: ignore[no-untyped-def]
    return (
        SqlAlchemyBookingRepository(sqlite_factory),
        SqlAlchemyClientRepository(sqlite_factory),
    )
