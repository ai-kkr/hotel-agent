"""Domain entities and aggregate roots.

Pure Python (stdlib only): ``domain`` depends on nothing external.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import ClassVar

from domain.enums import (
    DEFAULT_TOPIC_LABELS,
    BookingLifecycle,
    Channel,
    MessageDirection,
    SenderRole,
    TopicStatus,
)
from domain.ids import BookingId, ClientToken, EmailAddress, MessageId, TopicId


@dataclass
class HotelContact:
    """Identity and reachability of the hotel under negotiation."""

    hotel_name: str
    email: EmailAddress | None = None
    website: str | None = None
    language: str | None = None  # ISO-639-1 ("en","fr",...); None = unknown
    discovered: bool = False  # True if discovered via web rather than read from confirmation

    def __post_init__(self) -> None:
        if not self.hotel_name or not self.hotel_name.strip():
            raise ValueError("hotel_name must not be empty")

    @property
    def is_ready(self) -> bool:
        """A hotel is contactable once we have an email address."""
        return self.email is not None


@dataclass
class Topic:
    """A single negotiation topic (early check-in, upgrade, a wish, …)."""

    topic_id: TopicId
    label: str
    status: TopicStatus = TopicStatus.OPEN
    result: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("topic label must not be empty")

    @property
    def is_open(self) -> bool:
        return self.status == TopicStatus.OPEN

    @property
    def is_terminal(self) -> bool:
        return self.status in (TopicStatus.RESOLVED, TopicStatus.UNRESOLVED, TopicStatus.CANT_PROGRESS)

    def resolve(self, result: str) -> None:
        if not result.strip():
            raise ValueError("result must not be empty")
        self.status = TopicStatus.RESOLVED
        self.result = result

    def mark_unresolved(self, reason: str = "") -> None:
        self.status = TopicStatus.UNRESOLVED
        if reason.strip():
            self.result = reason

    def mark_cant_progress(self, reason: str) -> None:
        if not reason.strip():
            raise ValueError("reason must not be empty")
        self.status = TopicStatus.CANT_PROGRESS
        self.result = reason

    def reopen(self) -> None:
        """A follow-up may reopen a previously-resolved topic."""
        self.status = TopicStatus.OPEN
        self.result = None


@dataclass
class Message:
    """An inbound or outbound message on any channel."""

    message_id: MessageId
    booking_id: BookingId
    direction: MessageDirection
    channel: Channel
    body: str
    created_at: datetime
    subject: str | None = None
    sender: EmailAddress | None = None
    recipient: EmailAddress | None = None
    sender_role: SenderRole = SenderRole.SYSTEM
    idempotency_key: str | None = None  # outbound dedup

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("message body must not be empty")


@dataclass
class Booking:
    """Aggregate root: one booking = one conversation = one workflow = one agent thread."""

    booking_id: BookingId
    client_token: ClientToken
    hotel: HotelContact
    booking_ref: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    guests: list[str] = field(default_factory=list)
    room_type: str | None = None
    language: str = "en"  # language of correspondence with the hotel
    wishes: list[str] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    lifecycle: BookingLifecycle = BookingLifecycle.INTAKE
    report: str | None = None
    followup_attempts: int = 0

    # ---- construction ----

    @classmethod
    def start(
        cls,
        booking_id: BookingId,
        client_token: ClientToken,
        hotel: HotelContact,
        *,
        language: str = "en",
    ) -> Booking:
        """Begin a booking with default topics (early check-in, upgrade) in OPEN."""
        booking = cls(booking_id=booking_id, client_token=client_token, hotel=hotel, language=language)
        for label in DEFAULT_TOPIC_LABELS:
            booking._new_topic(label)
        return booking

    # ---- topics ----

    def _new_topic(self, label: str) -> Topic:
        topic = Topic(topic_id=self._next_topic_id(label), label=label)
        self.topics.append(topic)
        return topic

    def _next_topic_id(self, label: str) -> TopicId:
        # Deterministic, human-readable id scoped to the booking.
        slug = label.lower().replace(" ", "-")
        return f"{self.booking_id}:t:{slug}"

    def add_topic(self, label: str) -> Topic:
        """Add a wish-derived topic in OPEN."""
        if any(t.label.lower() == label.lower() for t in self.topics):
            raise ValueError(f"topic already exists: {label}")
        return self._new_topic(label)

    def add_wish(self, text: str) -> None:
        text = text.strip()
        if not text:
            raise ValueError("wish must not be empty")
        if text not in self.wishes:
            self.wishes.append(text)

    def topic(self, topic_id: TopicId) -> Topic:
        for t in self.topics:
            if t.topic_id == topic_id:
                return t
        raise KeyError(topic_id)

    def open_topics(self) -> list[Topic]:
        return [t for t in self.topics if t.is_open]

    def all_topics_terminal(self) -> bool:
        return bool(self.topics) and all(t.is_terminal for t in self.topics)

    # ---- lifecycle ----

    def advance(self, lifecycle: BookingLifecycle) -> None:
        self.lifecycle = lifecycle

    @property
    def is_cancelled(self) -> bool:
        return self.lifecycle == BookingLifecycle.CANCELLED

    @property
    def is_active(self) -> bool:
        """A booking is active unless it has reached a terminal lifecycle (cancelled or can't-progress)."""
        return self.lifecycle not in (BookingLifecycle.CANCELLED, BookingLifecycle.CANT_PROGRESS)

    def mark_cancelled(self) -> None:
        """Idempotently move the booking to CANCELLED (design D8).

        Repeated cancellation is a no-op: no further side-effects should be triggered by the caller.
        """
        self.lifecycle = BookingLifecycle.CANCELLED

    def increment_followup(self) -> int:
        self.followup_attempts += 1
        return self.followup_attempts

    def attach_report(self, report: str) -> None:
        if not report.strip():
            raise ValueError("report must not be empty")
        self.report = report

    def with_hotel_contact(self, hotel: HotelContact) -> Booking:
        """Return a copy with updated hotel contact/language (used after discovery)."""
        language = hotel.language or self.language
        return replace(self, hotel=hotel, language=language)


@dataclass
class Client:
    """A registered client, addressable by an unguessable token."""

    token: ClientToken
    email: EmailAddress
    name: str | None = None

    TOKEN_BYTES: ClassVar[int] = 12  # for generators in infrastructure; documented here


@dataclass(frozen=True)
class ChannelSession:
    """Binds a client to a per-channel address (design D5 / client-communication spec).

    The identity seam for non-email channels: outbound delivery resolves an address from a client
    (and vice-versa) without coupling to any specific channel. A client MAY have sessions on
    multiple channels (e.g. a Telegram ``chat_id``).

    ``address`` is channel-specific (Telegram chat id, WhatsApp phone, …); it is NOT an email.
    """

    client_token: ClientToken
    channel: Channel
    address: str  # channel-specific (e.g. Telegram chat_id)

    def __post_init__(self) -> None:
        if not self.client_token:
            raise ValueError("client_token must not be empty")
        if not self.address:
            raise ValueError("channel address must not be empty")
