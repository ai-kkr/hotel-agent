from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
import pytest
from httpx import ASGITransport

from domain.application import InboundDispatcher, IntakeService
from domain.entities import Booking, Client, HotelContact
from domain.events import ClientMessage, ConfirmForward, HotelReply
from domain.ids import BookingId, EmailAddress
from infrastructure.config import Settings
from infrastructure.mail.mailgun import MailgunWebhookNormalizer
from infrastructure.mail.signature import compute_signature
from infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryClientRepository,
)
from presentation.app import create_app
from presentation.container import build_webhook_deps

SIGNING_KEY = "key-test"


@dataclass
class RecordingGateway:
    started: list[ConfirmForward] = field(default_factory=list)
    hotel_replies: list[HotelReply] = field(default_factory=list)
    client_messages: list[ClientMessage] = field(default_factory=list)
    delivery_failures: list[tuple[BookingId, str, str]] = field(default_factory=list)

    async def start_booking(self, event: ConfirmForward) -> None:
        self.started.append(event)

    async def signal_hotel_reply(self, event: HotelReply) -> None:
        self.hotel_replies.append(event)

    async def signal_client_message(self, event: ClientMessage) -> None:
        self.client_messages.append(event)

    async def signal_delivery_failure(
        self, booking_id: BookingId, severity: str, description: str
    ) -> None:
        self.delivery_failures.append((booking_id, severity, description))


@pytest.fixture
def gateway() -> RecordingGateway:
    return RecordingGateway()


async def _make_client(
    gateway: RecordingGateway, *, seed_booking: bool = False
) -> tuple[httpx.AsyncClient, RecordingGateway]:
    clients = InMemoryClientRepository()
    bookings = InMemoryBookingRepository()
    await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
    if seed_booking:
        await bookings.save(
            Booking.start(
                booking_id="b1",
                client_token="tok",
                hotel=HotelContact(hotel_name="Grand", email=EmailAddress("hotel@grand.com")),
            )
        )
    dispatcher = InboundDispatcher(clients=clients, bookings=bookings, mail_domain="kkr-hotel.com")
    intake = IntakeService(clients=clients, gateway=gateway)
    settings = Settings(mailgun_signing_key=SIGNING_KEY, mail_domain="kkr-hotel.com")
    deps = build_webhook_deps(
        settings=settings,
        normalizer=MailgunWebhookNormalizer(fallback_clock=lambda: datetime(2026, 1, 1, tzinfo=UTC)),
        dispatcher=dispatcher,
        gateway=gateway,
        intake=intake,
    )
    app = create_app(webhook_deps=deps)
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test"), gateway


def _signed_form(fields: dict[str, str]) -> dict[str, str]:
    import time

    ts = str(int(time.time()))
    token = "tok123"
    form = {
        "timestamp": ts,
        "token": token,
        "signature": compute_signature(SIGNING_KEY, ts, token),
    }
    form.update(fields)
    return form


async def test_inbound_intake_starts_booking(gateway: RecordingGateway) -> None:
    client, gw = await _make_client(gateway)
    async with client:
        resp = await client.post(
            "/webhooks/mailgun/inbound",
            data=_signed_form(
                {
                    "recipient": "c.tok@kkr-hotel.com",
                    "sender": "client@example.com",
                    "subject": "Fwd: booking",
                    "body-plain": "confirmation body",
                }
            ),
        )
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 1
    assert len(gw.started) == 1
    assert gw.started[0].client_token == "tok"


async def test_inbound_hotel_reply_signals_workflow(gateway: RecordingGateway) -> None:
    client, gw = await _make_client(gateway, seed_booking=True)
    async with client:
        resp = await client.post(
            "/webhooks/mailgun/inbound",
            data=_signed_form(
                {
                    "recipient": "b.b1@kkr-hotel.com",
                    "sender": "hotel@grand.com",
                    "subject": "Re:",
                    "body-plain": "yes we can",
                }
            ),
        )
    assert resp.status_code == 200
    assert len(gw.hotel_replies) == 1
    assert gw.hotel_replies[0].booking_id == "b1"


async def test_inbound_rejects_bad_signature(gateway: RecordingGateway) -> None:
    client, _ = await _make_client(gateway)
    async with client:
        resp = await client.post(
            "/webhooks/mailgun/inbound",
            data={
                "timestamp": "1700000000",
                "token": "tok123",
                "signature": "deadbeef",
                "recipient": "c.tok@kkr-hotel.com",
                "from": "client@example.com",
            },
        )
    assert resp.status_code == 401


async def test_stub_inbound_accepted_without_signature(gateway: RecordingGateway) -> None:
    """Local-run: /webhooks/stub/inbound parses the payload with no signature verification."""
    from infrastructure.mail.stub import StubInboundNormalizer

    clients = InMemoryClientRepository()
    bookings = InMemoryBookingRepository()
    await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
    dispatcher = InboundDispatcher(clients=clients, bookings=bookings, mail_domain="kkr-hotel.com")
    intake = IntakeService(clients=clients, gateway=gateway)
    settings = Settings(mail_domain="kkr-hotel.com")
    deps = build_webhook_deps(
        settings=settings,
        normalizer=StubInboundNormalizer(fallback_clock=lambda: datetime(2026, 1, 1, tzinfo=UTC)),
        dispatcher=dispatcher,
        gateway=gateway,
        intake=intake,
    )
    app = create_app(webhook_deps=deps)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhooks/stub/inbound",
            data={
                "recipient": "c.tok@kkr-hotel.com",
                "sender": "client@example.com",
                "subject": "Fwd: booking",
                "body-plain": "confirmation body",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 1
    assert len(gateway.started) == 1



async def test_status_permanent_bounce_signals_failure(gateway: RecordingGateway) -> None:
    client, gw = await _make_client(gateway, seed_booking=True)
    async with client:
        resp = await client.post(
            "/webhooks/mailgun/status",
            data=_signed_form(
                {
                    "event": "bounced",
                    "severity": "permanent",
                    "recipient": "b.b1@kkr-hotel.com",
                    "error": "user unknown",
                }
            ),
        )
    assert resp.status_code == 204
    assert gw.delivery_failures == [("b1", "permanent", "user unknown")]


async def test_status_delivered_does_not_signal(gateway: RecordingGateway) -> None:
    client, gw = await _make_client(gateway, seed_booking=True)
    async with client:
        resp = await client.post(
            "/webhooks/mailgun/status",
            data=_signed_form(
                {"event": "delivered", "severity": "permanent", "recipient": "b.b1@kkr-hotel.com"}
            ),
        )
    assert resp.status_code == 204
    assert gw.delivery_failures == []


async def test_api_client_message_signals_followup(gateway: RecordingGateway) -> None:
    client, gw = await _make_client(gateway, seed_booking=True)
    async with client:
        resp = await client.post(
            "/api/client-message",
            json={"booking_id": "b1", "body": "also ask late checkout", "channel": "api"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"accepted": True, "booking_id": "b1"}
    assert len(gw.client_messages) == 1
    assert gw.client_messages[0].booking_id == "b1"
    assert gw.client_messages[0].body == "also ask late checkout"


async def test_api_client_message_rejects_empty_body(gateway: RecordingGateway) -> None:
    client, _ = await _make_client(gateway)
    async with client:
        resp = await client.post("/api/client-message", json={"booking_id": "b1", "body": ""})
    assert resp.status_code == 422


async def test_api_client_message_503_when_deps_not_configured() -> None:
    """When no ``webhook_deps`` is attached to ``app.state``, the provider must govern
    ``client_message`` via ``Depends`` and return the 503 "not configured" contract."""
    app = create_app()  # no webhook_deps -> app.state.webhook_deps unset
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/client-message",
            json={"booking_id": "b1", "body": "hello"},
        )
    assert resp.status_code == 503
    assert resp.json() == {"detail": "webhook dependencies not configured"}
