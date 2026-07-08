"""End-to-end Telegram-surface pipeline (design D1, D5, D6, D7, D8).

Offline integration of the chat surface: mailbox → chat-forward intake → workflow start → outbound
progress push (routed to the Telegram chat) → cancellation. Like ``test_pipeline``, this drives the
real services with recording fakes (no Temporal server, no real Telegram calls). A live Telegram +
Temporal E2E is additionally gated behind ``KKR_E2E_TELEGRAM`` (akin to ``KKR_E2E_TEMPORAL``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from domain.application import (
    CancellationService,
    ChatIntakeService,
    MailboxService,
)
from domain.enums import Channel
from domain.events import ChatForward
from infrastructure.mail.notifier import CoalescingClientNotifier, RoutingClientNotifier
from infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryChannelSessionRepository,
    InMemoryClientRepository,
)
from infrastructure.telegram.adapter import TelegramClientNotifier
from infrastructure.workflows.activities import ConciergeActivities
from infrastructure.workflows.dtos import BookingState, HotelContactData
from tests.workflows.test_activities import FakeGateway, FakeNotifier, FakeReporter


class RecordingBot:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_message(
        self, chat_id: str, text: str, reply_markup: dict[str, Any] | None = None
    ) -> None:
        self.sent.append((chat_id, text))

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> None: ...


class RecordingGateway:
    """WorkflowGateway fake that records starts/cancels."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.cancelled: list[str] = []

    async def start_booking(self, event: object) -> None:
        self.started.append(event.client_token)  # type: ignore[attr-defined]

    async def signal_hotel_reply(self, event: object) -> None: ...
    async def signal_client_message(self, event: object) -> None: ...
    async def signal_delivery_failure(self, *args: object) -> None: ...

    async def cancel_booking(self, booking_id: str) -> None:
        self.cancelled.append(booking_id)


@pytest.fixture
def stack() -> dict[str, Any]:
    clients = InMemoryClientRepository()
    sessions = InMemoryChannelSessionRepository()
    bookings = InMemoryBookingRepository()
    gateway = RecordingGateway()
    bot = RecordingBot()

    mailbox = MailboxService(
        clients=clients, sessions=sessions, mail_domain="kkr-hotel.com", token_factory=lambda: "tok"
    )
    intake = ChatIntakeService(sessions=sessions, clients=clients, gateway=gateway)

    # Outbound: routed to Telegram (the client has a chat session), coalesced.
    telegram_notifier = TelegramClientNotifier(bot=bot, sessions=sessions)
    email_notifier = FakeNotifier()
    notifier = CoalescingClientNotifier(
        inner=RoutingClientNotifier(
            sessions=sessions, email=email_notifier, channels={Channel.TELEGRAM: telegram_notifier}
        )
    )

    activities = ConciergeActivities(
        extractor=object(),  # type: ignore[arg-type]
        discoverer=object(),  # type: ignore[arg-type]
        negotiator=object(),  # type: ignore[arg-type]
        reporter=FakeReporter(),  # type: ignore[arg-type]
        gateway=FakeGateway(),  # type: ignore[arg-type]
        notifier=notifier,  # type: ignore[arg-type]
        bookings=bookings,
        mail_domain="kkr-hotel.com",
    )
    cancellation = CancellationService(bookings=bookings, gateway=gateway, notifier=notifier)
    return {
        "clients": clients,
        "sessions": sessions,
        "bookings": bookings,
        "gateway": gateway,
        "bot": bot,
        "mailbox": mailbox,
        "intake": intake,
        "activities": activities,
        "cancellation": cancellation,
        "email_notifier": email_notifier,
    }


class TestChatSurfaceE2E:
    async def test_mailbox_then_intake_starts_booking(self, stack: dict) -> None:
        mailbox: MailboxService = stack["mailbox"]
        await mailbox.resolve_or_create(Channel.TELEGRAM, "chat:1")

        intake: ChatIntakeService = stack["intake"]
        outcome = await intake.handle(
            ChatForward(
                client_token="",
                chat_id="chat:1",
                cover_text="please early check-in",
                forwarded_payload="confirmation body",
                received_at=datetime.now(tz=UTC),
            )
        )
        assert outcome.started is True
        assert stack["gateway"].started == ["tok"]

    async def test_progress_push_routes_to_telegram_chat(self, stack: dict) -> None:
        bookings: InMemoryBookingRepository = stack["bookings"]
        from domain.entities import Booking, HotelContact
        from domain.ids import EmailAddress

        await stack["mailbox"].resolve_or_create(Channel.TELEGRAM, "chat:1")
        await bookings.save(
            Booking.start("b1", "tok", HotelContact(hotel_name="Grand", email=EmailAddress("h@grand.com")))
        )
        activities: ConciergeActivities = stack["activities"]
        await activities.notify_progress("b1", "sent", "Message sent", "I've sent the request.")
        # Delivered to the client's Telegram chat (not email).
        assert stack["bot"].sent[-1] == ("chat:1", "Message sent\n\nI've sent the request.")
        assert stack["email_notifier"].notified == []

    async def test_cancel_flow_marks_cancelled_and_notifies(self, stack: dict) -> None:
        bookings: InMemoryBookingRepository = stack["bookings"]
        from domain.entities import Booking, HotelContact
        from domain.ids import EmailAddress

        await stack["mailbox"].resolve_or_create(Channel.TELEGRAM, "chat:1")
        await bookings.save(
            Booking.start("b1", "tok", HotelContact(hotel_name="Grand", email=EmailAddress("h@grand.com")))
        )
        cancellation: CancellationService = stack["cancellation"]
        outcome = await cancellation.cancel("b1")
        assert outcome.cancelled is True
        assert stack["gateway"].cancelled == ["b1"]
        saved = await bookings.get("b1")
        assert saved is not None and saved.is_cancelled
        # The cancellation event reached the chat.
        assert any("cancelled" in text.lower() for _chat, text in stack["bot"].sent)

    async def test_report_after_cancel_reflects_cancellation(self, stack: dict) -> None:
        activities: ConciergeActivities = stack["activities"]
        state = BookingState(
            booking_id="b1",
            client_token="tok",
            hotel=HotelContactData(hotel_name="Grand", email="h@grand.com"),
            lifecycle="cancelled",
        )
        report = await activities.build_report(state)
        assert "cancelled" in report.lower()
