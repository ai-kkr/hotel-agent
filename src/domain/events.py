"""Domain events: the unified inbound vocabulary.

Every inbound channel event (email webhook, API, future messenger webhooks) normalizes into one of
these. They start or signal the ``BookingWorkflow``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.enums import Channel
from domain.ids import BookingId, ClientToken, EmailAddress


@dataclass(frozen=True)
class InboundEmail:
    """Provider-neutral representation of one inbound email, before dispatch.

    Produced by an ``InboundMailNormalizer``; the :class:`domain.application.InboundDispatcher`
    turns it into domain events (``ConfirmForward`` / ``HotelReply`` / ``ClientMessage``) by
    inspecting the recipient local-part and the sender.
    """

    recipients: list[str]  # full recipient addresses (may include non-domain addresses)
    sender: EmailAddress
    subject: str
    body: str
    received_at: datetime
    provider_message_id: str | None = None


@dataclass(frozen=True)
class ConfirmForward:
    """A client forwarded a booking confirmation to ``c.<token>@``."""

    client_token: ClientToken
    sender_email: EmailAddress  # must match the client's registered email (SPF/DKIM verified)
    subject: str
    cover_text: str  # client's accompanying note (may contain wishes)
    forwarded_payload: str  # the forwarded confirmation body (text)
    received_at: datetime
    provider_message_id: str | None = None


@dataclass(frozen=True)
class HotelReply:
    """A reply from the hotel, arriving on ``b.<booking>@``."""

    booking_id: BookingId
    from_email: EmailAddress
    subject: str | None
    body: str
    received_at: datetime
    provider_message_id: str | None = None


@dataclass(frozen=True)
class ClientMessage:
    """Follow-up input from the client over any channel (email on v1).

    ``booking_id`` is None when the channel cannot resolve it (e.g. a messenger session not yet
    bound to a booking); the dispatcher then resolves it.
    """

    booking_id: BookingId | None
    body: str
    received_at: datetime
    channel: Channel = Channel.EMAIL
    from_email: EmailAddress | None = None
    provider_message_id: str | None = None


DomainEvent = ConfirmForward | HotelReply | ClientMessage
