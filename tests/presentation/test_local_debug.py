from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from httpx import ASGITransport

from domain.ids import BookingId, EmailAddress, MessageId
from infrastructure.mail.stub import OutboundEmailRecord, StubOutboundGateway
from presentation.app import create_app


class _Repo:
    async def add_message(self, message):  # type: ignore[no-untyped-def]
        return message.message_id


def _record(subject: str, body: str) -> OutboundEmailRecord:
    return OutboundEmailRecord(
        message_id=MessageId("stub:b1:initial"),
        booking_id=BookingId("b1"),
        to=EmailAddress("hotel@grand.com"),
        sender=EmailAddress("b.b1@kkr-hotel.com"),
        reply_to=EmailAddress("b.b1@kkr-hotel.com"),
        subject=subject,
        body=body,
        idempotency_key="b1:initial",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def gateway() -> StubOutboundGateway:
    gw = StubOutboundGateway(repo=_Repo(), mail_domain="kkr-hotel.com")  # type: ignore[arg-type]
    gw.outbox.append(_record("Hotel request", "Dear hotel, please arrange early check-in."))
    return gw


class TestLocalOutboxEndpoint:
    async def test_outbox_returns_recorded_emails(self, gateway: StubOutboundGateway) -> None:
        app = create_app()
        app.state.outbox_gateway = gateway
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/_local/outbox")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        msg = body["messages"][0]
        assert msg["subject"] == "Hotel request"
        assert msg["body"] == "Dear hotel, please arrange early check-in."
        assert msg["to"] == "hotel@grand.com"
        assert msg["booking_id"] == "b1"

    async def test_outbox_404_when_not_attached(self) -> None:
        app = create_app()  # no outbox_gateway on state
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/_local/outbox")
        assert resp.status_code == 404

    async def test_outbox_reflects_new_sends(self, gateway: StubOutboundGateway) -> None:
        app = create_app()
        app.state.outbox_gateway = gateway
        await gateway.send(
            booking_id="b1",
            to=EmailAddress("hotel@grand.com"),
            sender=EmailAddress("b.b1@kkr-hotel.com"),
            reply_to=EmailAddress("b.b1@kkr-hotel.com"),
            subject="Follow-up",
            body="any update?",
            idempotency_key="b1:followup1",
        )
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/_local/outbox")
        subjects = [m["subject"] for m in resp.json()["messages"]]
        assert subjects == ["Hotel request", "Follow-up"]
