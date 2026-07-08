"""Client notification adapters (spec 8.1, 8.2; design D7).

The :class:`domain.ports.ClientNotifier` port is generalized (design D7) from "deliver the report"
to "deliver any progress event" (:class:`domain.ports.ProgressEvent`). A report is one ``kind``
among many (contact_ready, sent, hotel_replied, report, …).

Adapters provided here:

- :class:`EmailClientNotifier` — delivers over email (Mailgun on v1). Reply-To is the booking-scoped
  address so the client can reply to follow up.
- :class:`RoutingClientNotifier` — routes an event to the client's configured channel via
  :class:`ChannelSessionRepository` (Telegram if the client has a chat session, else email).
- :class:`CoalescingClientNotifier` — dedupes consecutive identical events to avoid flooding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from domain.enums import Channel
from domain.ids import conversation_address
from domain.ports import (
    ChannelSessionRepository,
    ClientNotifier,
    ClientRepository,
    OutboundMailGateway,
    ProgressEvent,
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Lifecycle/topic transitions that are user-visible (design D7 / client-communication spec).
# Internal transitions (extracted, awaiting_client_followup, …) are NOT pushed to the client.
USER_VISIBLE_KINDS: frozenset[str] = frozenset(
    {"contact_ready", "sent", "hotel_replied", "report", "cancelled", "cant_progress"}
)


def _slug(text: str) -> str:
    return _NON_ALNUM.sub("-", text.lower()).strip("-")[:40] or "notify"


class EmailClientNotifier(ClientNotifier):
    """Deliver a progress event to the client's registered email."""

    def __init__(
        self,
        gateway: OutboundMailGateway,
        clients: ClientRepository,
        mail_domain: str,
    ) -> None:
        self._gateway = gateway
        self._clients = clients
        self._mail_domain = mail_domain

    async def notify(self, event: ProgressEvent) -> None:
        client = await self._clients.by_token(event.client_token)
        if client is None:
            return  # nothing to deliver to (client unknown); logged upstream
        reply_to = conversation_address(event.booking_id, self._mail_domain)
        await self._gateway.send(
            booking_id=event.booking_id,
            to=client.email,
            sender=reply_to,
            reply_to=reply_to,
            subject=event.subject,
            body=event.body,
            idempotency_key=f"{event.booking_id}:notify:{event.kind}:{_slug(event.subject)}",
        )


@dataclass
class RoutingClientNotifier(ClientNotifier):
    """Route a progress event to the client's configured channel (design D7 / 7.3).

    If the client has a Telegram :class:`ChannelSession`, the event is delivered to their chat;
    otherwise it falls back to email. A client is notified on exactly one channel per event.
    """

    sessions: ChannelSessionRepository
    email: ClientNotifier
    # Per-channel notifiers; Telegram is the first concrete surface. Defaults to email-only.
    channels: dict[Channel, ClientNotifier] = field(default_factory=dict)

    async def notify(self, event: ProgressEvent) -> None:
        for channel, notifier in self.channels.items():
            address = await self.sessions.address_for(event.client_token, channel)
            if address is not None:
                await notifier.notify(event)
                return
        await self.email.notify(event)


@dataclass
class CoalescingClientNotifier(ClientNotifier):
    """Suppress flooding from rapid/duplicate transitions (design D7 risk, task 7.2).

    Drops consecutive identical events (same booking + kind + subject) and non-user-visible kinds.
    The idempotency key on the underlying adapter additionally dedupes across activity retries.
    """

    inner: ClientNotifier
    visible_kinds: frozenset[str] = USER_VISIBLE_KINDS
    _seen: set[tuple[str, str, str]] = field(default_factory=set)

    async def notify(self, event: ProgressEvent) -> None:
        if event.kind not in self.visible_kinds:
            return
        key = (event.booking_id, event.kind, event.subject)
        if key in self._seen:
            return
        self._seen.add(key)
        await self.inner.notify(event)
