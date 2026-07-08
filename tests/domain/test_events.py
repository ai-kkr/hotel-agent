from __future__ import annotations

from datetime import UTC, datetime

from domain.enums import Channel
from domain.events import ClientMessage, ConfirmForward, HotelReply
from domain.ids import EmailAddress


def now() -> datetime:
    return datetime.now(tz=UTC)


class TestConfirmForward:
    def test_construction(self) -> None:
        e = ConfirmForward(
            client_token="tok",
            sender_email=EmailAddress("c@x.com"),
            subject="Fwd: booking",
            cover_text="please get early check-in",
            forwarded_payload="confirmation body",
            received_at=now(),
        )
        assert e.client_token == "tok"
        assert e.cover_text and e.forwarded_payload


class TestHotelReply:
    def test_construction(self) -> None:
        e = HotelReply(
            booking_id="b1",
            from_email=EmailAddress("h@hotel.com"),
            subject="Re:",
            body="Sure",
            received_at=now(),
        )
        assert e.booking_id == "b1" and e.body == "Sure"


class TestClientMessage:
    def test_email_followup(self) -> None:
        e = ClientMessage(
            booking_id="b1",
            body="thanks, also ask late checkout",
            received_at=now(),
            channel=Channel.EMAIL,
            from_email=EmailAddress("c@x.com"),
        )
        assert e.booking_id == "b1" and e.channel is Channel.EMAIL

    def test_booking_id_may_be_none(self) -> None:
        e = ClientMessage(booking_id=None, body="hi", received_at=now())
        assert e.booking_id is None
