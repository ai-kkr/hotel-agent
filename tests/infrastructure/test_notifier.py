from __future__ import annotations

import pytest

from domain.entities import Booking, Client, HotelContact
from domain.ids import EmailAddress
from infrastructure.mail.notifier import EmailClientNotifier
from infrastructure.persistence.in_memory import InMemoryClientRepository


class RecordingGateway:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    async def send(self, *, booking_id, to, sender, reply_to, subject, body, idempotency_key):  # type: ignore[no-untyped-def]
        self.sent.append(
            {
                "booking_id": booking_id,
                "to": to,
                "sender": sender,
                "reply_to": reply_to,
                "subject": subject,
                "body": body,
                "idempotency_key": idempotency_key,
            }
        )
        return f"mg:{idempotency_key}"


def _booking() -> Booking:
    return Booking.start("b1", "tok", HotelContact(hotel_name="Grand", email=EmailAddress("h@grand.com")))


@pytest.fixture
def clients() -> InMemoryClientRepository:
    return InMemoryClientRepository()


@pytest.fixture
def gateway() -> RecordingGateway:
    return RecordingGateway()


class TestEmailClientNotifier:
    async def test_delivers_to_registered_client(self, clients, gateway) -> None:  # type: ignore[no-untyped-def]
        await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
        notifier = EmailClientNotifier(gateway, clients, "kkr-hotel.com")
        await notifier.notify(_booking(), "Your report", "body here")
        assert len(gateway.sent) == 1
        sent = gateway.sent[0]
        assert sent["to"] == EmailAddress("client@example.com")
        assert sent["reply_to"].value == "b.b1@kkr-hotel.com"  # type: ignore[attr-defined]
        assert sent["idempotency_key"] == "b1:notify:your-report"

    async def test_noop_when_client_missing(self, clients, gateway) -> None:  # type: ignore[no-untyped-def]
        notifier = EmailClientNotifier(gateway, clients, "kkr-hotel.com")
        await notifier.notify(_booking(), "S", "B")
        assert gateway.sent == []

    async def test_distinct_idempotency_keys_per_subject(self, clients, gateway) -> None:  # type: ignore[no-untyped-def]
        await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
        notifier = EmailClientNotifier(gateway, clients, "kkr-hotel.com")
        await notifier.notify(_booking(), "Your report", "b1")
        await notifier.notify(_booking(), "We need info", "b2")
        keys = {s["idempotency_key"] for s in gateway.sent}
        assert keys == {"b1:notify:your-report", "b1:notify:we-need-info"}
