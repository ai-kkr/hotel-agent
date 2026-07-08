"""Mailgun adapters: inbound webhook normalizer + outbound sending gateway."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from domain.entities import Message
from domain.enums import Channel, MessageDirection, SenderRole
from domain.events import InboundEmail
from domain.ids import BookingId, EmailAddress, MessageId
from domain.ports import BookingRepository
from infrastructure.mail.html import extract_body_text


def _first(payload: Mapping[str, object], *keys: str, default: str = "") -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return default


def _parse_date(raw: str, fallback: datetime) -> datetime:
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return fallback
    if parsed is None:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class MailgunWebhookNormalizer:
    """Parse a Mailgun inbound-webhook payload into a provider-neutral :class:`InboundEmail`."""

    def __init__(self, *, fallback_clock: Callable[[], datetime] | None = None) -> None:
        self._now = fallback_clock or (lambda: datetime.now(tz=UTC))

    def parse(self, payload: Mapping[str, object]) -> InboundEmail:
        recipients_raw = _first(payload, "recipient", "to")
        recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
        sender_raw = _first(payload, "sender", "from")
        if not sender_raw:
            raise ValueError("mailgun webhook missing sender/from")
        # Mailgun may include a display name ("Name <a@b.com>"); extract the address.
        sender = _extract_address(sender_raw)
        subject = _first(payload, "subject")
        body = extract_body_text(payload)
        message_id = _first(payload, "Message-Id", "message-id") or None
        received_at = _parse_date(_first(payload, "Date", "date"), fallback=self._now())
        return InboundEmail(
            recipients=recipients,
            sender=EmailAddress(sender),
            subject=subject,
            body=body,
            received_at=received_at,
            provider_message_id=message_id or None,
        )


def _extract_address(raw: str) -> str:
    """Extract a bare email address from a header value like ``"Name" <a@b.com>``."""
    if "<" in raw and ">" in raw:
        inner = raw[raw.find("<") + 1 : raw.find(">")]
        return inner.strip()
    return raw.strip()


class MailgunOutboundGateway:
    """Send outbound email through Mailgun's API, idempotent per ``idempotency_key``.

    Idempotency is enforced at the message-store level: we record the outbound message before
    sending, so a retried activity finds the key already present and skips the HTTP call — no
    duplicate email (design D12).
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        mail_domain: str,
        repo: BookingRepository,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._mail_domain = mail_domain
        self._repo = repo
        self._client = client
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    async def send(
        self,
        *,
        booking_id: BookingId,
        to: EmailAddress,
        sender: EmailAddress,
        reply_to: EmailAddress,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> MessageId:
        message_id = f"mg:{idempotency_key}"
        record = Message(
            message_id=message_id,
            booking_id=booking_id,
            direction=MessageDirection.OUTBOUND,
            channel=Channel.EMAIL,
            subject=subject,
            body=body,
            sender=sender,
            recipient=to,
            sender_role=SenderRole.SYSTEM,
            idempotency_key=idempotency_key,
            created_at=self._clock(),
        )
        inserted = await self._repo.add_message(record)
        if inserted is None:
            # Already sent on a previous attempt (activity retry) — do not resend.
            return message_id

        await self._post_to_mailgun(to=to, sender=sender, reply_to=reply_to, subject=subject, body=body)
        return message_id

    async def _post_to_mailgun(
        self, *, to: EmailAddress, sender: EmailAddress, reply_to: EmailAddress, subject: str, body: str
    ) -> None:
        url = f"{self._base_url}/v3/{self._mail_domain}/messages"
        data = {
            "from": str(sender),
            "to": str(to),
            "subject": subject,
            "text": body,
            "h:Reply-To": str(reply_to),
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            response = await client.post(url, data=data, auth=("api", self._api_key))
            response.raise_for_status()
        finally:
            if owns_client:
                await client.aclose()
