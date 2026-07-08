from __future__ import annotations

import pytest

from domain.entities import Booking, ChannelSession, Client, HotelContact
from domain.enums import Channel
from domain.ids import EmailAddress
from domain.ports import ProgressEvent
from infrastructure.mail.notifier import (
    CoalescingClientNotifier,
    EmailClientNotifier,
    RoutingClientNotifier,
)
from infrastructure.persistence.in_memory import (
    InMemoryChannelSessionRepository,
    InMemoryClientRepository,
)


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


class RecordingNotifier:
    def __init__(self) -> None:
        self.events: list[ProgressEvent] = []

    async def notify(self, event: ProgressEvent) -> None:
        self.events.append(event)


def _booking() -> Booking:
    return Booking.start("b1", "tok", HotelContact(hotel_name="Grand", email=EmailAddress("h@grand.com")))


def _event(kind: str = "report", subject: str = "Your report", body: str = "body here") -> ProgressEvent:
    return ProgressEvent(client_token="tok", booking_id="b1", kind=kind, subject=subject, body=body)


@pytest.fixture
def clients() -> InMemoryClientRepository:
    return InMemoryClientRepository()


@pytest.fixture
def gateway() -> RecordingGateway:
    return RecordingGateway()


class TestEmailClientNotifier:
    async def test_delivers_progress_event_to_registered_client(self, clients, gateway) -> None:  # type: ignore[no-untyped-def]
        await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
        notifier = EmailClientNotifier(gateway, clients, "kkr-hotel.com")
        await notifier.notify(_event())
        assert len(gateway.sent) == 1
        sent = gateway.sent[0]
        assert sent["to"] == EmailAddress("client@example.com")
        assert sent["reply_to"].value == "b.b1@kkr-hotel.com"  # type: ignore[attr-defined]
        # idempotency key now includes the kind
        assert sent["idempotency_key"] == "b1:notify:report:your-report"

    async def test_noop_when_client_missing(self, clients, gateway) -> None:  # type: ignore[no-untyped-def]
        notifier = EmailClientNotifier(gateway, clients, "kkr-hotel.com")
        await notifier.notify(_event())
        assert gateway.sent == []

    async def test_distinct_idempotency_keys_per_kind_and_subject(self, clients, gateway) -> None:  # type: ignore[no-untyped-def]
        await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
        notifier = EmailClientNotifier(gateway, clients, "kkr-hotel.com")
        await notifier.notify(_event(kind="report", subject="Your report"))
        await notifier.notify(_event(kind="sent", subject="Message sent"))
        keys = {s["idempotency_key"] for s in gateway.sent}
        assert keys == {"b1:notify:report:your-report", "b1:notify:sent:message-sent"}


class TestRoutingClientNotifier:
    async def test_routes_to_telegram_when_session_exists(self, clients) -> None:  # type: ignore[no-untyped-def]
        sessions = InMemoryChannelSessionRepository()
        await sessions.upsert(
            ChannelSession(client_token="tok", channel=Channel.TELEGRAM, address="chat:1")
        )
        email = RecordingNotifier()
        telegram = RecordingNotifier()
        router = RoutingClientNotifier(sessions=sessions, email=email, channels={Channel.TELEGRAM: telegram})
        await router.notify(_event())
        assert len(telegram.events) == 1
        assert email.events == []  # not duplicated on email

    async def test_falls_back_to_email_without_session(self, clients) -> None:  # type: ignore[no-untyped-def]
        sessions = InMemoryChannelSessionRepository()
        email = RecordingNotifier()
        telegram = RecordingNotifier()
        router = RoutingClientNotifier(sessions=sessions, email=email, channels={Channel.TELEGRAM: telegram})
        await router.notify(_event())
        assert len(email.events) == 1
        assert telegram.events == []


class TestCoalescingClientNotifier:
    async def test_drops_duplicate_consecutive_events(self) -> None:
        inner = RecordingNotifier()
        notifier = CoalescingClientNotifier(inner=inner)
        await notifier.notify(_event(kind="sent", subject="Message sent"))
        await notifier.notify(_event(kind="sent", subject="Message sent"))  # duplicate → dropped
        assert len(inner.events) == 1

    async def test_passes_through_distinct_events(self) -> None:
        inner = RecordingNotifier()
        notifier = CoalescingClientNotifier(inner=inner)
        await notifier.notify(_event(kind="sent", subject="Message sent"))
        await notifier.notify(_event(kind="hotel_replied", subject="The hotel replied"))
        assert [e.kind for e in inner.events] == ["sent", "hotel_replied"]

    async def test_drops_non_user_visible_kind(self) -> None:
        inner = RecordingNotifier()
        notifier = CoalescingClientNotifier(inner=inner)
        await notifier.notify(_event(kind="extracted", subject="internal"))  # internal → dropped
        assert inner.events == []
