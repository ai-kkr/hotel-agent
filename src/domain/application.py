"""Application / use-case services orchestrating domain ports.

These depend only on domain ports (never infrastructure), so they are fully testable with the
in-memory repositories.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.errors import UnauthorizedSender, UnknownClientToken
from domain.events import ClientMessage, ConfirmForward, DomainEvent, HotelReply, InboundEmail
from domain.ids import INTAKE_PREFIX, route
from domain.ports import BookingRepository, ClientRepository, WorkflowGateway


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


__all__ = ["INTAKE_PREFIX", "InboundDispatcher", "IntakeService"]


@dataclass
class IntakeService:
    """Handle a forwarded confirmation: authenticate the client, then start the workflow.

    The sender must match the client's registered email (the SPF/DKIM-verified address surfaced by
    the mail provider). Default topics (early-checkin, room-upgrade) and wish-derived topics are
    initialized inside the workflow via the extraction activity (spec 7.2, 7.3).
    """

    clients: ClientRepository
    gateway: WorkflowGateway

    async def handle(self, event: ConfirmForward) -> None:
        client = await self.clients.by_token(event.client_token)
        if client is None:
            raise UnknownClientToken(event.client_token)
        if event.sender_email != client.email:
            raise UnauthorizedSender(
                f"sender {event.sender_email} does not match registered email {client.email}"
            )
        await self.gateway.start_booking(event)
