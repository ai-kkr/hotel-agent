"""Domain ports (interfaces). Outer layers implement these.

``domain`` only declares protocols; it never imports infrastructure. This is the seam that makes
channels swappable (D8) and the agent replacable/testable with fakes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from domain.entities import Booking, ChannelSession, Client, Message
from domain.enums import Channel
from domain.events import ClientMessage, ConfirmForward, DomainEvent, HotelReply, InboundEmail
from domain.extraction import ExtractedBooking
from domain.ids import BookingId, ClientToken, EmailAddress, MessageId
from domain.intents import AgentIntent, SearchDone, Trigger

# --- Repositories (Postgres-backed) -------------------------------------------------


@runtime_checkable
class ClientRepository(Protocol):
    async def by_token(self, token: ClientToken) -> Client | None: ...

    async def add(self, client: Client) -> None: ...


@runtime_checkable
class ChannelSessionRepository(Protocol):
    """Resolve a client ↔ channel-address binding (design D5 / client-communication spec).

    Inbound chat events resolve a client from a channel address; outbound delivery resolves a
    channel address from a client. ``upsert`` binds a (channel, address) to a client token and is
    idempotent.
    """

    async def client_for(self, channel: Channel, address: str) -> ClientToken | None: ...

    async def address_for(self, token: ClientToken, channel: Channel) -> str | None: ...

    async def upsert(self, session: ChannelSession) -> None: ...


@runtime_checkable
class BookingRepository(Protocol):
    async def get(self, booking_id: BookingId) -> Booking | None: ...

    async def save(self, booking: Booking) -> None: ...

    async def add_message(self, message: Message) -> MessageId | None: ...

    async def messages(self, booking_id: BookingId) -> list[Message]: ...

    async def bookings_for_client(self, token: ClientToken) -> list[Booking]: ...


# --- Channel gateways (per-provider, per-channel adapters) ---------------------------


@runtime_checkable
class OutboundMailGateway(Protocol):
    """Send an outbound email. Idempotent on ``idempotency_key`` across activity retries."""

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
    ) -> MessageId: ...


@runtime_checkable
class InboundMailNormalizer(Protocol):
    """Parse a provider webhook payload into a provider-neutral :class:`InboundEmail` (pure)."""

    def parse(self, payload: Mapping[str, Any]) -> InboundEmail: ...


@runtime_checkable
class ClientNotifier(Protocol):
    """Deliver a progress event to the client over the configured channel (design D7).

    Generalized from "deliver the report" to "deliver any progress event". A report is one ``kind``
    among many (contact_ready, sent, hotel_replied, report, …). The adapter resolves the client's
    channel address via :class:`ChannelSessionRepository` and renders per channel (email keeps its
    adapter; Telegram has its own). Idempotent on ``booking_id`` + ``kind`` across activity retries.
    """

    async def notify(self, event: ProgressEvent) -> None: ...


@dataclass(frozen=True)
class ProgressEvent:
    """One user-visible progress notification (design D7 / client-communication spec).

    Carried by the generalized :class:`ClientNotifier`. ``subject`` is a short title; ``body`` is the
    detail. For the email channel, ``subject`` is the email subject.
    """

    client_token: ClientToken
    booking_id: BookingId
    kind: str  # e.g. "contact_ready", "sent", "hotel_replied", "report"
    subject: str
    body: str

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("progress event kind must not be empty")
        if not self.subject.strip():
            raise ValueError("progress event subject must not be empty")
        if not self.body.strip():
            raise ValueError("progress event body must not be empty")


@runtime_checkable
class WorkflowGateway(Protocol):
    """Bridge from inbound events to the durable workflow layer (Temporal, wired in Group 6).

    Presentation depends on this port rather than Temporal directly, keeping the HTTP layer
    thin and fully testable with a recording fake.
    """

    async def start_booking(self, event: ConfirmForward) -> None: ...

    async def signal_hotel_reply(self, event: HotelReply) -> None: ...

    async def signal_client_message(self, event: ClientMessage) -> None: ...

    async def signal_delivery_failure(
        self, booking_id: BookingId, severity: str, description: str
    ) -> None: ...

    async def cancel_booking(self, booking_id: BookingId) -> None: ...


# --- Agent ports (LangGraph-backed; faked in tests) ---------------------------------


@runtime_checkable
class ConfirmationExtractor(Protocol):
    """Extract structured booking data + wishes from a forwarded confirmation."""

    async def extract(self, event: ConfirmForward) -> ExtractedBooking: ...


@runtime_checkable
class ContactDiscoverer(Protocol):
    """Discover the hotel contact email and correspondence language via the web."""

    async def discover(self, hotel_name: str, hint_website: str | None) -> SearchDone: ...


@runtime_checkable
class NegotiationAgent(Protocol):
    """The per-booking turn-brain. Reads the trigger, returns an intent (no side-effects)."""

    async def turn(self, booking_id: BookingId, trigger: Trigger, booking: Booking) -> AgentIntent: ...


@runtime_checkable
class ReportBuilder(Protocol):
    """Build the final client-facing report from a booking's topic outcomes."""

    async def build(self, booking: Booking) -> str: ...


__all__ = [
    "BookingRepository",
    "ChannelSessionRepository",
    "ClientMessage",
    "ClientNotifier",
    "ClientRepository",
    "ConfirmationExtractor",
    "ContactDiscoverer",
    "DomainEvent",
    "HotelReply",
    "InboundMailNormalizer",
    "NegotiationAgent",
    "OutboundMailGateway",
    "ProgressEvent",
    "ReportBuilder",
    "WorkflowGateway",
]
