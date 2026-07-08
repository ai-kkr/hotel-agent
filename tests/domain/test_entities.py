from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.entities import Booking, Client, HotelContact, Message, Topic
from domain.enums import (
    DEFAULT_TOPIC_LABELS,
    TOPIC_EARLY_CHECKIN,
    TOPIC_ROOM_UPGRADE,
    BookingLifecycle,
    Channel,
    MessageDirection,
    TopicStatus,
)
from domain.ids import EmailAddress


def hotel(name: str = "Grand Hotel") -> HotelContact:
    return HotelContact(hotel_name=name, email=EmailAddress("stay@grand.com"))


class TestHotelContact:
    def test_requires_name(self) -> None:
        with pytest.raises(ValueError):
            HotelContact(hotel_name="   ")

    def test_not_ready_without_email(self) -> None:
        assert HotelContact(hotel_name="X").is_ready is False

    def test_ready_with_email(self) -> None:
        assert hotel().is_ready is True


class TestTopic:
    def test_resolve_sets_result(self) -> None:
        t = Topic(topic_id="b:t:x", label="x")
        t.resolve("granted at 10:00")
        assert t.status is TopicStatus.RESOLVED
        assert t.result == "granted at 10:00"
        assert t.is_terminal and not t.is_open

    def test_resolve_requires_nonempty(self) -> None:
        t = Topic(topic_id="b:t:x", label="x")
        with pytest.raises(ValueError):
            t.resolve("  ")

    def test_cant_progress_requires_reason(self) -> None:
        t = Topic(topic_id="b:t:x", label="x")
        with pytest.raises(ValueError):
            t.mark_cant_progress("  ")

    def test_reopen(self) -> None:
        t = Topic(topic_id="b:t:x", label="x")
        t.resolve("ok")
        t.reopen()
        assert t.is_open and t.result is None

    def test_unresolved_optional_reason(self) -> None:
        t = Topic(topic_id="b:t:x", label="x")
        t.mark_unresolved("no answer")
        assert t.status is TopicStatus.UNRESOLVED and t.result == "no answer"

    def test_label_must_not_be_empty(self) -> None:
        with pytest.raises(ValueError):
            Topic(topic_id="b:t:x", label="  ")


class TestBooking:
    def test_start_creates_default_open_topics(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        labels = [t.label for t in b.topics]
        assert labels == list(DEFAULT_TOPIC_LABELS)
        assert all(t.is_open for t in b.topics)
        assert b.lifecycle is BookingLifecycle.INTAKE
        assert b.language == "en"

    def test_topic_ids_are_scoped_and_deterministic(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        ids = {t.topic_id for t in b.topics}
        assert ids == {f"b1:t:{TOPIC_EARLY_CHECKIN}", f"b1:t:{TOPIC_ROOM_UPGRADE}"}

    def test_add_topic_rejects_duplicate(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        with pytest.raises(ValueError):
            b.add_topic(TOPIC_ROOM_UPGRADE)

    def test_add_wish_dedups(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        b.add_wish("high floor")
        b.add_wish("high floor")
        assert b.wishes == ["high floor"]

    def test_add_wish_rejects_empty(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        with pytest.raises(ValueError):
            b.add_wish("  ")

    def test_open_topics_and_terminal(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        b.topic(f"b1:t:{TOPIC_EARLY_CHECKIN}").resolve("ok")
        assert len(b.open_topics()) == 1
        assert not b.all_topics_terminal()
        b.topic(f"b1:t:{TOPIC_ROOM_UPGRADE}").resolve("ok")
        assert b.all_topics_terminal()

    def test_topic_lookup_raises_on_unknown(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        with pytest.raises(KeyError):
            b.topic("nope")

    def test_with_hotel_contact_updates_language(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        new_hotel = HotelContact(hotel_name="Grand", email=EmailAddress("x@y.com"), language="fr")
        b2 = b.with_hotel_contact(new_hotel)
        assert b2.language == "fr" and b2.hotel.email is not None
        # original untouched
        assert b.language == "en"

    def test_increment_followup(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        assert b.increment_followup() == 1
        assert b.followup_attempts == 1

    def test_attach_report(self) -> None:
        b = Booking.start("b1", "tok", hotel())
        with pytest.raises(ValueError):
            b.attach_report("  ")
        b.attach_report("report body")
        assert b.report == "report body"


class TestMessage:
    def test_requires_body(self) -> None:
        with pytest.raises(ValueError):
            Message(
                message_id="m1",
                booking_id="b1",
                direction=MessageDirection.OUTBOUND,
                channel=Channel.EMAIL,
                body="",
                created_at=datetime.now(tz=UTC),
            )

    def test_roundtrip(self) -> None:
        m = Message(
            message_id="m1",
            booking_id="b1",
            direction=MessageDirection.INBOUND,
            channel=Channel.EMAIL,
            body="hi",
            created_at=datetime.now(tz=UTC),
            sender=EmailAddress("h@x.com"),
        )
        assert m.body == "hi"


class TestClient:
    def test_minimal(self) -> None:
        c = Client(token="tok", email=EmailAddress("c@x.com"))
        assert c.token == "tok" and c.email.value == "c@x.com"
