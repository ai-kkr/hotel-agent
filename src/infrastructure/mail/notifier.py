"""Email :class:`domain.ports.ClientNotifier` adapter (spec 8.1, 8.2).

Delivers reports / notifications to the client's registered email over the messaging gateway
(Mailgun on v1). Reply-To is the booking-scoped address so the client can simply reply to follow
up. The port is channel-agnostic; Telegram/WhatsApp/native app adapters can be added later without
touching intake/negotiation (spec 8.5).
"""

from __future__ import annotations

import re

from domain.entities import Booking
from domain.ids import conversation_address
from domain.ports import ClientNotifier, ClientRepository, OutboundMailGateway

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _NON_ALNUM.sub("-", text.lower()).strip("-")[:40] or "notify"


class EmailClientNotifier(ClientNotifier):
    """Notify the client by email, looked up from their booking's client token."""

    def __init__(
        self,
        gateway: OutboundMailGateway,
        clients: ClientRepository,
        mail_domain: str,
    ) -> None:
        self._gateway = gateway
        self._clients = clients
        self._mail_domain = mail_domain

    async def notify(self, booking: Booking, subject: str, body: str) -> None:
        client = await self._clients.by_token(booking.client_token)
        if client is None:
            return  # nothing to deliver to (client unknown); logged upstream
        reply_to = conversation_address(booking.booking_id, self._mail_domain)
        await self._gateway.send(
            booking_id=booking.booking_id,
            to=client.email,
            sender=reply_to,
            reply_to=reply_to,
            subject=subject,
            body=body,
            idempotency_key=f"{booking.booking_id}:notify:{_slug(subject)}",
        )
