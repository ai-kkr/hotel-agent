from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from domain.ids import EmailAddress
from infrastructure.mail.mailgun import MailgunOutboundGateway, MailgunWebhookNormalizer
from infrastructure.persistence.in_memory import InMemoryBookingRepository


class TestMailgunWebhookNormalizer:
    def setup_method(self) -> None:
        self.fixed = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.normalizer = MailgunWebhookNormalizer(fallback_clock=lambda: self.fixed)

    def test_parses_basic_fields(self) -> None:
        payload = {
            "recipient": "c.abc@kkr-hotel.com",
            "sender": "client@example.com",
            "subject": "Fwd: your booking",
            "body-plain": "full body",
            "Date": "Mon, 01 Jun 2026 09:30:00 +0000",
            "Message-Id": "<abc@mail.example.com>",
        }
        email = self.normalizer.parse(payload)
        assert email.recipients == ["c.abc@kkr-hotel.com"]
        assert email.sender == EmailAddress("client@example.com")
        assert email.subject == "Fwd: your booking"
        assert email.body == "full body"
        assert email.provider_message_id == "<abc@mail.example.com>"
        assert email.received_at == datetime(2026, 6, 1, 9, 30, tzinfo=UTC)

    def test_extracts_address_from_display_name(self) -> None:
        payload = {"recipient": "b.42@kkr-hotel.com", "sender": "Hotel <stay@hotel.com>"}
        email = self.normalizer.parse(payload)
        assert email.sender == EmailAddress("stay@hotel.com")

    def test_multiple_recipients_split(self) -> None:
        payload = {"recipient": "b.42@kkr-hotel.com, other@elsewhere.com", "from": "x@y.com"}
        email = self.normalizer.parse(payload)
        assert email.recipients == ["b.42@kkr-hotel.com", "other@elsewhere.com"]

    def test_uses_fallback_clock_when_no_date(self) -> None:
        payload = {"recipient": "b.1@kkr-hotel.com", "from": "x@y.com"}
        email = self.normalizer.parse(payload)
        assert email.received_at == self.fixed

    def test_missing_sender_raises(self) -> None:
        with pytest.raises(ValueError):
            self.normalizer.parse({"recipient": "b.1@kkr-hotel.com"})

    def test_html_only_body_falls_back_to_html(self) -> None:
        payload = {
            "recipient": "c.abc@kkr-hotel.com",
            "sender": "client@example.com",
            "subject": "Fwd: booking",
            "body-plain": "",  # no plaintext part → HTML-only confirmation
            "body-html": "<html><body><p>Booking at <b>Grand Hotel</b></p><p>Ref: ABC123</p></body></html>",
        }
        email = self.normalizer.parse(payload)
        assert "Grand Hotel" in email.body
        assert "ABC123" in email.body
        assert "<html>" not in email.body.lower()

    def test_plain_preferred_over_html(self) -> None:
        payload = {
            "recipient": "c.abc@kkr-hotel.com",
            "sender": "client@example.com",
            "body-plain": "plain wins",
            "body-html": "<p>html loses</p>",
        }
        assert self.normalizer.parse(payload).body == "plain wins"

    def test_empty_plain_and_html_yields_empty_body(self) -> None:
        payload = {"recipient": "c.abc@kkr-hotel.com", "sender": "client@example.com"}
        assert self.normalizer.parse(payload).body == ""


class TestMailgunOutboundGatewayIdempotency:
    @pytest.fixture
    def repo(self) -> InMemoryBookingRepository:
        return InMemoryBookingRepository()

    @pytest.fixture
    def gateway(self, repo: InMemoryBookingRepository) -> MailgunOutboundGateway:
        return MailgunOutboundGateway(
            api_key="key",
            base_url="https://api.mailgun.net",
            mail_domain="kkr-hotel.com",
            repo=repo,
            clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
        )

    @respx.mock
    async def test_sends_once_then_dedups_on_retry(
        self, gateway: MailgunOutboundGateway, repo: InMemoryBookingRepository
    ) -> None:
        route = respx.post("https://api.mailgun.net/v3/kkr-hotel.com/messages").mock(
            return_value=httpx.Response(200, json={"id": "<mg-1>"})
        )

        common = dict(
            booking_id="b1",
            to=EmailAddress("hotel@grand.com"),
            sender=EmailAddress("b1@kkr-hotel.com"),
            reply_to=EmailAddress("b1@kkr-hotel.com"),
            subject="Hi",
            body="Body",
        )
        first = await gateway.send(**common, idempotency_key="b1:initial")  # type: ignore[arg-type]
        second = await gateway.send(**common, idempotency_key="b1:initial")  # type: ignore[arg-type]

        assert first == "mg:b1:initial"
        assert second == "mg:b1:initial"  # same id, not re-sent
        assert route.call_count == 1  # HTTP POST happened exactly once
        msgs = await repo.messages("b1")
        assert len(msgs) == 1

    @respx.mock
    async def test_distinct_steps_both_sent(
        self, gateway: MailgunOutboundGateway, repo: InMemoryBookingRepository
    ) -> None:
        respx.post("https://api.mailgun.net/v3/kkr-hotel.com/messages").mock(
            return_value=httpx.Response(200, json={"id": "<x>"})
        )
        base = dict(
            booking_id="b1",
            to=EmailAddress("h@grand.com"),
            sender=EmailAddress("b1@kkr-hotel.com"),
            reply_to=EmailAddress("b1@kkr-hotel.com"),
            subject="Hi",
            body="Body",
        )
        await gateway.send(**base, idempotency_key="b1:initial")  # type: ignore[arg-type]
        await gateway.send(**base, idempotency_key="b1:followup1")  # type: ignore[arg-type]
        msgs = await repo.messages("b1")
        assert {m.idempotency_key for m in msgs} == {"b1:initial", "b1:followup1"}

    @respx.mock
    async def test_http_error_propagates(
        self, gateway: MailgunOutboundGateway, repo: InMemoryBookingRepository
    ) -> None:
        respx.post("https://api.mailgun.net/v3/kkr-hotel.com/messages").mock(
            return_value=httpx.Response(500, text="boom")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await gateway.send(
                booking_id="b1",
                to=EmailAddress("h@grand.com"),
                sender=EmailAddress("b1@kkr-hotel.com"),
                reply_to=EmailAddress("b1@kkr-hotel.com"),
                subject="Hi",
                body="Body",
                idempotency_key="b1:initial",
            )
        # The intent was recorded before the failed send; a retry will dedup on the same key.
        msgs = await repo.messages("b1")
        assert len(msgs) == 1
