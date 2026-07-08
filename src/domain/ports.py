"""Domain ports (interfaces). Outer layers implement these.

``domain`` only declares protocols; it never imports infrastructure. This is the seam that makes
channels swappable (D8) and the agent replacable/testable with fakes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from domain.entities import Booking, Client, Message
from domain.events import ClientMessage, ConfirmForward, DomainEvent, HotelReply, InboundEmail
from domain.extraction import ExtractedBooking
from domain.ids import BookingId, ClientToken, EmailAddress, MessageId
from domain.intents import AgentIntent, SearchDone, Trigger

# --- Repositories (Postgres-backed) -------------------------------------------------


@runtime_checkable
class ClientRepository(Protocol):
    async def by_token(self, token: ClientToken) -> Client | None: ...


@runtime_checkable
class BookingRepository(Protocol):
    async def get(self, booking_id: BookingId) -> Booking | None: ...

    async def save(self, booking: Booking) -> None: ...

    async def add_message(self, message: Message) -> MessageId | None: ...

    async def messages(self, booking_id: BookingId) -> list[Message]: ...


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
    """Deliver a report / notification to the client over the configured channel (email on v1)."""

    async def notify(self, booking: Booking, subject: str, body: str) -> None: ...


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
    "ReportBuilder",
    "WorkflowGateway",
]
