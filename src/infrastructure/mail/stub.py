"""Stub mail adapters for local development / testing (design D2, D3 of ``local-agent-run-harness``).

No real network: outbound messages are recorded to an in-memory outbox for inspection, and the
inbound normalizer accepts the same payload shape as Mailgun without verifying any signature. Both
implement the same domain ports (``OutboundMailGateway`` / ``InboundMailNormalizer``) so the rest of
the system is unchanged — activation is a config switch (``KKR_MAIL_PROVIDER=stub``).

Idempotency mirrors :class:`MailgunOutboundGateway`: the message is recorded on the booking
repository *before* it is "sent" (here: appended to the outbox), so a retried activity with the same
``idempotency_key`` finds it already present and is a no-op — no duplicate outbox entry.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from domain.entities import Message
from domain.enums import Channel, MessageDirection, SenderRole
from domain.events import InboundEmail
from domain.ids import BookingId, EmailAddress, MessageId
from domain.ports import BookingRepository
from infrastructure.logging import get_logger
from infrastructure.mail.html import extract_body_text

_logger = get_logger(__name__)


def _first(payload: Mapping[str, object], *keys: str, default: str = "") -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return default


def _parse_date(raw: str, fallback: datetime) -> datetime:
    from email.utils import parsedate_to_datetime

    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return fallback
    if parsed is None:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _extract_address(raw: str) -> str:
    """Extract a bare email address from a header value like ``"Name" <a@b.com>``."""
    if "<" in raw and ">" in raw:
        inner = raw[raw.find("<") + 1 : raw.find(">")]
        return inner.strip()
    return raw.strip()


@dataclass
class OutboundEmailRecord:
    """A captured outbound email — what would have been sent over the wire in production."""

    message_id: MessageId
    booking_id: BookingId
    to: EmailAddress
    sender: EmailAddress
    reply_to: EmailAddress
    subject: str
    body: str
    idempotency_key: str
    created_at: datetime


class StubOutboundGateway:
    """``OutboundMailGateway`` that records messages to an in-memory outbox instead of sending.

    The outbox (``.outbox``) is a plain list callers can inspect in tests / local debugging. Like the
    Mailgun adapter, a message is persisted via ``repo.add_message`` *before* being recorded, so the
    idempotency contract (no duplicate on activity retry) holds identically.
    """

    def __init__(
        self,
        *,
        repo: BookingRepository,
        mail_domain: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repo = repo
        self._mail_domain = mail_domain
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self.outbox: list[OutboundEmailRecord] = []

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
        message_id = f"stub:{idempotency_key}"
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
            # Already sent on a previous attempt (activity retry) — do not duplicate.
            return message_id

        self.outbox.append(
            OutboundEmailRecord(
                message_id=message_id,
                booking_id=booking_id,
                to=to,
                sender=sender,
                reply_to=reply_to,
                subject=subject,
                body=body,
                idempotency_key=idempotency_key,
                created_at=record.created_at,
            )
        )
        _logger.info(
            "outbound.stub.recorded",
            booking_id=str(booking_id),
            to=str(to),
            subject=subject,
            idempotency_key=idempotency_key,
            message_id=message_id,
            mail_domain=self._mail_domain,
        )
        return message_id


class StubInboundNormalizer:
    """``InboundMailNormalizer`` that parses a Mailgun-shaped payload without signature checks.

    Accepts the same fields as :class:`MailgunWebhookNormalizer` so a local developer can emulate an
    inbound email (hotel reply / client message) with a plain POST or a direct call.
    """

    def __init__(self, *, fallback_clock: Callable[[], datetime] | None = None) -> None:
        self._now = fallback_clock or (lambda: datetime.now(tz=UTC))

    def parse(self, payload: Mapping[str, object]) -> InboundEmail:
        recipients_raw = _first(payload, "recipient", "to")
        recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
        sender_raw = _first(payload, "sender", "from")
        if not sender_raw:
            raise ValueError("stub inbound payload missing sender/from")
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
