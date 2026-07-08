"""Tests for the stub mail adapters (local-run-harness, tasks 2.1-2.4)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.ids import BookingId, EmailAddress
from infrastructure.mail.factory import build_inbound_normalizer, build_outbound_gateway
from infrastructure.mail.stub import (
    StubInboundNormalizer,
    StubOutboundGateway,
)
from infrastructure.persistence.in_memory import InMemoryBookingRepository


class TestStubOutboundGateway:
    @pytest.fixture
    def repo(self) -> InMemoryBookingRepository:
        return InMemoryBookingRepository()

    @pytest.fixture
    def gateway(self, repo: InMemoryBookingRepository) -> StubOutboundGateway:
        return StubOutboundGateway(
            repo=repo,
            mail_domain="kkr-hotel.com",
            clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
        )

    async def test_records_to_outbox_without_http(self, gateway: StubOutboundGateway) -> None:
        message_id = await gateway.send(
            booking_id=BookingId("b1"),
            to=EmailAddress("hotel@example.com"),
            sender=EmailAddress("b.b1@kkr-hotel.com"),
            reply_to=EmailAddress("b.b1@kkr-hotel.com"),
            subject="early check-in?",
            body="hello",
            idempotency_key="b1:compose_initial",
        )
        assert message_id == "stub:b1:compose_initial"
        assert len(gateway.outbox) == 1
        record = gateway.outbox[0]
        assert record.booking_id == BookingId("b1")
        assert record.to == EmailAddress("hotel@example.com")
        assert record.subject == "early check-in?"
        assert record.body == "hello"
        assert record.idempotency_key == "b1:compose_initial"

    async def test_idempotent_send_does_not_duplicate(
        self, gateway: StubOutboundGateway, repo: InMemoryBookingRepository
    ) -> None:
        kwargs = {
            "booking_id": BookingId("b1"),
            "to": EmailAddress("hotel@example.com"),
            "sender": EmailAddress("b.b1@kkr-hotel.com"),
            "reply_to": EmailAddress("b.b1@kkr-hotel.com"),
            "subject": "hi",
            "body": "body",
            "idempotency_key": "b1:step",
        }
        first = await gateway.send(**kwargs)
        second = await gateway.send(**kwargs)
        assert first == second == "stub:b1:step"
        assert len(gateway.outbox) == 1
        # The repository recorded exactly one outbound message.
        messages = await repo.messages(BookingId("b1"))
        assert len(messages) == 1


class TestStubInboundNormalizer:
    def setup_method(self) -> None:
        self.fixed = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.normalizer = StubInboundNormalizer(fallback_clock=lambda: self.fixed)

    def test_parses_basic_fields_without_signature(self) -> None:
        payload = {
            "recipient": "b.42@kkr-hotel.com",
            "sender": "stay@hotel.com",
            "subject": "Re: early check-in",
            "body-plain": "yes, we can",
            "Date": "Mon, 01 Jun 2026 09:30:00 +0000",
            "Message-Id": "<reply@hotel.com>",
        }
        email = self.normalizer.parse(payload)
        assert email.recipients == ["b.42@kkr-hotel.com"]
        assert email.sender == EmailAddress("stay@hotel.com")
        assert email.subject == "Re: early check-in"
        assert email.body == "yes, we can"
        assert email.provider_message_id == "<reply@hotel.com>"
        assert email.received_at == datetime(2026, 6, 1, 9, 30, tzinfo=UTC)

    def test_extracts_address_from_display_name(self) -> None:
        email = self.normalizer.parse(
            {"recipient": "b.1@kkr-hotel.com", "from": "Hotel <stay@hotel.com>"}
        )
        assert email.sender == EmailAddress("stay@hotel.com")

    def test_uses_fallback_clock_when_no_date(self) -> None:
        email = self.normalizer.parse({"recipient": "b.1@kkr-hotel.com", "from": "x@y.com"})
        assert email.received_at == self.fixed

    def test_missing_sender_raises(self) -> None:
        with pytest.raises(ValueError):
            self.normalizer.parse({"recipient": "b.1@kkr-hotel.com"})

    def test_html_only_body_falls_back_to_html(self) -> None:
        payload = {
            "recipient": "b.42@kkr-hotel.com",
            "sender": "stay@hotel.com",
            "subject": "Re: early check-in",
            "body-plain": "",  # HTML-only reply
            "body-html": "<p>We can offer <b>early check-in</b> at 11:00.</p>",
        }
        email = self.normalizer.parse(payload)
        assert "early check-in" in email.body
        assert "11:00" in email.body
        assert "<p>" not in email.body


class TestStubFactorySelection:
    def test_factory_returns_stub_adapters(self) -> None:
        from infrastructure.config import Settings

        settings = Settings(mail_provider="stub", mail_domain="kkr-hotel.com")
        assert isinstance(build_inbound_normalizer(settings), StubInboundNormalizer)
        assert isinstance(build_outbound_gateway(settings), StubOutboundGateway)

    def test_factory_default_remains_mailgun(self) -> None:
        from infrastructure.config import Settings
        from infrastructure.mail.mailgun import (
            MailgunOutboundGateway,
            MailgunWebhookNormalizer,
        )

        # Pin the provider explicitly so the test is independent of a developer's .env.
        settings = Settings(mail_provider="mailgun")
        assert isinstance(build_inbound_normalizer(settings), MailgunWebhookNormalizer)
        assert isinstance(build_outbound_gateway(settings), MailgunOutboundGateway)
