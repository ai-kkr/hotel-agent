"""In-memory repository implementations.

Used in tests and as fakes for the agent/workflow. No external dependencies.
"""

from __future__ import annotations

from domain.entities import Booking, ChannelSession, Client, Message
from domain.enums import Channel
from domain.ids import BookingId, ClientToken, MessageId


class InMemoryClientRepository:
    def __init__(self, clients: dict[ClientToken, Client] | None = None) -> None:
        self._clients: dict[ClientToken, Client] = dict(clients or {})

    async def by_token(self, token: ClientToken) -> Client | None:
        return self._clients.get(token)

    async def add(self, client: Client) -> None:
        self._clients[client.token] = client


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._bookings: dict[BookingId, Booking] = {}
        self._messages: dict[BookingId, list[Message]] = {}
        self._idempotency_keys: set[str] = set()

    async def get(self, booking_id: BookingId) -> Booking | None:
        return self._bookings.get(booking_id)

    async def save(self, booking: Booking) -> None:
        self._bookings[booking.booking_id] = booking

    async def add_message(self, message: Message) -> MessageId | None:
        """Insert a message; idempotent on ``idempotency_key``.

        Returns the message_id if inserted, None if a message with the same idempotency key
        already exists (dedup on activity retry).
        """
        if message.idempotency_key and message.idempotency_key in self._idempotency_keys:
            return None
        if message.idempotency_key:
            self._idempotency_keys.add(message.idempotency_key)
        self._messages.setdefault(message.booking_id, []).append(message)
        return message.message_id

    async def messages(self, booking_id: BookingId) -> list[Message]:
        return list(self._messages.get(booking_id, []))

    async def bookings_for_client(self, token: ClientToken) -> list[Booking]:
        return [b for b in self._bookings.values() if b.client_token == token]


class InMemoryChannelSessionRepository:
    def __init__(self) -> None:
        self._by_address: dict[tuple[str, str], ChannelSession] = {}

    async def client_for(self, channel: Channel, address: str) -> ClientToken | None:
        session = self._by_address.get((channel.value, address))
        return session.client_token if session else None

    async def address_for(self, token: ClientToken, channel: Channel) -> str | None:
        for (chan, _addr), session in self._by_address.items():
            if chan == channel.value and session.client_token == token:
                return session.address
        return None

    async def upsert(self, session: ChannelSession) -> None:
        key = (session.channel.value, session.address)
        existing = self._by_address.get(key)
        if existing is not None and existing.client_token != session.client_token:
            raise ValueError(f"channel address {session.address!r} already bound to another client")
        self._by_address[key] = session
