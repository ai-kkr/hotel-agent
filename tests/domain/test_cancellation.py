from __future__ import annotations

import pytest

from domain.application import CancellationService
from domain.entities import Booking, HotelContact
from domain.enums import BookingLifecycle
from domain.ids import EmailAddress
from domain.ports import ProgressEvent
from infrastructure.persistence.in_memory import InMemoryBookingRepository


class RecordingGateway:
    def __init__(self) -> None:
        self.cancelled: list[str] = []
        self.started: list[object] = []

    async def start_booking(self, event: object) -> None: ...
    async def signal_hotel_reply(self, event: object) -> None: ...
    async def signal_client_message(self, event: object) -> None: ...
    async def signal_delivery_failure(self, *args: object) -> None: ...

    async def cancel_booking(self, booking_id: str) -> None:
        self.cancelled.append(booking_id)


class RecordingNotifier:
    def __init__(self) -> None:
        self.events: list[ProgressEvent] = []

    async def notify(self, event: ProgressEvent) -> None:
        self.events.append(event)


def _booking(lifecycle: str = "in_conversation") -> Booking:
    b = Booking.start(
        "b1", "tok", HotelContact(hotel_name="Grand", email=EmailAddress("h@grand.com"))
    )
    b.advance(BookingLifecycle(lifecycle))
    return b


@pytest.fixture
def setup() -> tuple[CancellationService, RecordingGateway, InMemoryBookingRepository, RecordingNotifier]:
    bookings = InMemoryBookingRepository()
    gateway = RecordingGateway()
    notifier = RecordingNotifier()
    svc = CancellationService(bookings=bookings, gateway=gateway, notifier=notifier)
    return svc, gateway, bookings, notifier


class TestCancellation:
    async def test_cancel_active_booking(self, setup: tuple) -> None:
        svc, gateway, bookings, notifier = setup
        await bookings.save(_booking("in_conversation"))
        outcome = await svc.cancel("b1")
        assert outcome.cancelled is True and outcome.already_cancelled is False
        assert gateway.cancelled == ["b1"]
        saved = await bookings.get("b1")
        assert saved is not None and saved.is_cancelled
        # client notified with a "cancelled" progress event
        assert [e.kind for e in notifier.events] == ["cancelled"]

    async def test_idempotent_recancel(self, setup: tuple) -> None:
        svc, gateway, bookings, notifier = setup
        await bookings.save(_booking("cancelled"))
        outcome = await svc.cancel("b1")
        assert outcome.cancelled is True and outcome.already_cancelled is True
        # No second workflow-cancel side-effect, no second notification.
        assert gateway.cancelled == []
        assert notifier.events == []

    async def test_unknown_booking_not_cancelled(self, setup: tuple) -> None:
        svc, gateway, _bookings, notifier = setup
        outcome = await svc.cancel("nope")
        assert outcome.cancelled is False
        assert gateway.cancelled == []
        assert notifier.events == []

    async def test_report_reflects_cancellation(self) -> None:
        from infrastructure.workflows.activities import ConciergeActivities
        from infrastructure.workflows.dtos import BookingState, HotelContactData

        class _Reporter:
            async def build(self, booking: Booking) -> str:
                return "Topics summary."

        bookings = InMemoryBookingRepository()
        activities = ConciergeActivities(
            extractor=object(),  # type: ignore[arg-type]
            discoverer=object(),  # type: ignore[arg-type]
            negotiator=object(),  # type: ignore[arg-type]
            reporter=_Reporter(),  # type: ignore[arg-type]
            gateway=object(),  # type: ignore[arg-type]
            notifier=object(),  # type: ignore[arg-type]
            bookings=bookings,
            mail_domain="kkr-hotel.com",
        )
        state = BookingState(
            booking_id="b1",
            client_token="tok",
            hotel=HotelContactData(hotel_name="Grand", email="h@grand.com"),
            lifecycle="cancelled",
        )
        report = await activities.build_report(state)
        assert "cancelled" in report.lower()
        assert "Topics summary." in report  # still deliverable, with the original content appended
