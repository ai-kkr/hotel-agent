"""Application / use-case services orchestrating domain ports.

These depend only on domain ports (never infrastructure), so they are fully testable with the
in-memory repositories.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from domain.entities import ChannelSession, Client
from domain.enums import Channel
from domain.errors import UnauthorizedSender, UnknownClientToken
from domain.events import (
    ChatForward,
    ClientMessage,
    ConfirmForward,
    DomainEvent,
    HotelReply,
    InboundEmail,
)
from domain.ids import INTAKE_PREFIX, ClientToken, EmailAddress, intake_address, route
from domain.ports import (
    BookingRepository,
    ChannelSessionRepository,
    ClientNotifier,
    ClientRepository,
    ProgressEvent,
    WorkflowGateway,
)


@dataclass
class InboundDispatcher:
    """Classify a provider-neutral :class:`InboundEmail` into domain events.

    Dispatch is by recipient local-part + sender (design D6):

    * ``c.<token>@``  → :class:`ConfirmForward` (a client forwarding a confirmation).
    * ``b.<booking>@`` → :class:`HotelReply` (sender is not the booking's client) or
      :class:`ClientMessage` (sender is the booking's client — a follow-up).
    * any other local-part is ignored (returns ``[]``).

    For intake, the sender must match the client's registered email; otherwise the event is
    still produced (the intake handler enforces SPF/DKIM/identity and rejects mismatches).
    """

    clients: ClientRepository
    bookings: BookingRepository
    mail_domain: str

    async def dispatch(self, email: InboundEmail) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for recipient in email.recipients:
            local, _, domain = recipient.partition("@")
            if domain.lower() != self.mail_domain.lower():
                continue
            routed = route(local)
            if routed.is_intake and routed.token:
                events.append(self._confirm_forward(email, routed.token))
            elif routed.is_conversation and routed.booking_id:
                event = await self._classify_conversation(email, routed.booking_id)
                if event is not None:
                    events.append(event)
        return events

    @staticmethod
    def _confirm_forward(email: InboundEmail, token: str) -> ConfirmForward:
        # cover_text vs forwarded_payload separation is the agent's job (ConfirmationExtractor);
        # pass the full body as payload and the subject as a cover hint.
        return ConfirmForward(
            client_token=token,
            sender_email=email.sender,
            subject=email.subject,
            cover_text=email.subject,
            forwarded_payload=email.body,
            received_at=email.received_at,
            provider_message_id=email.provider_message_id,
        )

    async def _classify_conversation(
        self, email: InboundEmail, booking_id: str
    ) -> DomainEvent | None:
        booking = await self.bookings.get(booking_id)
        if booking is None:
            # Reply to an unknown booking: nothing to do (logged upstream).
            return None
        client = await self.clients.by_token(booking.client_token)
        if client is not None and email.sender == client.email:
            return ClientMessage(
                booking_id=booking_id,
                body=email.body,
                received_at=email.received_at,
                from_email=email.sender,
                provider_message_id=email.provider_message_id,
            )
        return HotelReply(
            booking_id=booking_id,
            from_email=email.sender,
            subject=email.subject,
            body=email.body,
            received_at=email.received_at,
            provider_message_id=email.provider_message_id,
        )


__all__ = [
    "INTAKE_PREFIX",
    "CancelOutcome",
    "CancellationService",
    "ChatIntakeOutcome",
    "ChatIntakeService",
    "InboundDispatcher",
    "IntakeService",
    "MailboxService",
]


@dataclass
class MailboxService:
    """Resolve or lazily create a client's private intake mailbox (design D5).

    ``resolve_or_create`` is the implementation of ``get_user_mailbox``. Given a channel identity
    (e.g. a Telegram ``chat_id``), it returns the existing private ``c.<token>@<domain>`` address or
    creates a :class:`Client` (token), binds the channel identity via a :class:`ChannelSession`, and
    returns the new private address. The address is never shown to the user; it is the identity
    anchor and the email-channel intake target.

    The client's ``email`` IS the private intake address (the anchor for chat-origin clients, who
    have no personal email on file). Idempotent: a repeat call for the same channel address returns
    the same existing address without creating a duplicate.
    """

    clients: ClientRepository
    sessions: ChannelSessionRepository
    mail_domain: str
    token_factory: Callable[[], ClientToken]  # injected; infrastructure uses secrets.token_hex

    async def resolve_or_create(self, channel: Channel, address: str) -> EmailAddress:
        token = await self.sessions.client_for(channel, address)
        if token is not None:
            return intake_address(token, self.mail_domain)
        token = self.token_factory()
        mailbox = intake_address(token, self.mail_domain)
        await self.clients.add(Client(token=token, email=mailbox))
        await self.sessions.upsert(
            ChannelSession(client_token=token, channel=channel, address=address)
        )
        return mailbox


@dataclass
class IntakeService:
    """Handle a forwarded confirmation: authenticate the client, then start the workflow.

    Authentication rules (design D5):
    * For chat-origin clients (no registered email, client.email == c.<token>@<domain>):
      authenticate by token possession (the recipient address proves ownership).
    * For email-channel clients (registered email on file): enforce strict sender matching
      (sender must equal client.email).

    Default topics (early-checkin, room-upgrade) and wish-derived topics are initialized inside
    the workflow via the extraction activity (spec 7.2, 7.3).
    """

    clients: ClientRepository
    gateway: WorkflowGateway

    async def handle(self, event: ConfirmForward) -> None:
        client = await self.clients.by_token(event.client_token)
        if client is None:
            raise UnknownClientToken(event.client_token)

        # Capability-auth for chat-origin clients: if the client's email is a mailbox address
        # (c.<token>@<domain>), authenticate by token possession (skip sender check).
        if str(client.email).startswith(f"{INTAKE_PREFIX}"):
            # Chat-origin client: the recipient address (c.<token>@) proves ownership
            await self.gateway.start_booking(event)
            return

        # Email-channel client: enforce strict sender matching
        if event.sender_email != client.email:
            raise UnauthorizedSender(
                f"sender {event.sender_email} does not match registered email {client.email}"
            )
        await self.gateway.start_booking(event)


@dataclass(frozen=True)
class ChatIntakeOutcome:
    """Result of a chat-forward intake (design D6).

    ``started`` is False (with ``needs_mailbox=True``) when the chat has no bound session — the
    caller prompts the client to initialize their mailbox via ``get_user_mailbox``.
    """

    started: bool
    needs_mailbox: bool = False
    client_token: ClientToken | None = None


@dataclass
class ChatIntakeService:
    """Handle a chat-forwarded confirmation (design D6).

    Authenticated by the chat's :class:`ChannelSession` (no SPF/DKIM — the private mailbox is the
    secret identity anchor, design D5). Resolves the owning client, builds the standard
    :class:`ConfirmForward` the core already expects, and delegates to the same ``start_booking``
    path as an emailed confirmation — extraction is shared, never duplicated (D2). Cover-text wishes
    flow through identically to the email path.
    """

    sessions: ChannelSessionRepository
    clients: ClientRepository
    gateway: WorkflowGateway

    async def handle(self, event: ChatForward) -> ChatIntakeOutcome:
        token = await self.sessions.client_for(event.channel, event.chat_id)
        if token is None:
            # Unknown chat: do not start a booking; caller prompts to init the mailbox.
            return ChatIntakeOutcome(started=False, needs_mailbox=True)
        client = await self.clients.by_token(token)
        if client is None:
            # Session bound but client vanished (data inconsistency): treat as unknown.
            return ChatIntakeOutcome(started=False, needs_mailbox=True)
        forward = ConfirmForward(
            client_token=token,
            sender_email=client.email,  # the anchor mailbox; auth already done via the session
            subject="(chat forward)",
            cover_text=event.cover_text,
            forwarded_payload=event.forwarded_payload,
            received_at=event.received_at,
        )
        await self.gateway.start_booking(forward)
        return ChatIntakeOutcome(started=True, client_token=token)


@dataclass(frozen=True)
class CancelOutcome:
    """Result of a cancellation request (design D8).

    ``already_cancelled`` is True for an idempotent re-cancel (no side-effects re-run). Unknown
    bookings are not cancelled.
    """

    cancelled: bool
    already_cancelled: bool = False
    reason: str = ""


@dataclass
class CancellationService:
    """Execute a ``CancelBooking`` intent (design D8): cancel the workflow + mark CANCELLED.

    The surface agent emits the intent; this service performs the side-effects (the agent has none).
    Cancellation is idempotent: re-cancelling an already-cancelled booking is a no-op. The client is
    notified via the generalized notifier (a ``cancelled`` progress event).
    """

    bookings: BookingRepository
    gateway: WorkflowGateway
    notifier: ClientNotifier | None = None

    async def cancel(self, booking_id: str) -> CancelOutcome:
        booking = await self.bookings.get(booking_id)
        if booking is None:
            return CancelOutcome(cancelled=False, reason="unknown_booking")
        if booking.is_cancelled:
            return CancelOutcome(cancelled=True, already_cancelled=True)
        await self.gateway.cancel_booking(booking_id)
        booking.mark_cancelled()
        await self.bookings.save(booking)
        if self.notifier is not None:
            await self.notifier.notify(
                ProgressEvent(
                    client_token=booking.client_token,
                    booking_id=booking_id,
                    kind="cancelled",
                    subject="Booking cancelled",
                    body=(
                        f"I've cancelled your request for {booking.hotel.hotel_name}. "
                        "No further messages will be sent to the hotel."
                    ),
                )
            )
        return CancelOutcome(cancelled=True)
