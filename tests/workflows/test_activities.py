from __future__ import annotations

from datetime import date

from domain.entities import Booking, HotelContact
from domain.enums import TopicStatus
from domain.events import ConfirmForward
from domain.extraction import ExtractedBooking
from domain.ids import BookingId, EmailAddress
from domain.intents import AgentIntent, Resolved, SendEmail, TopicResolution
from infrastructure.persistence.in_memory import InMemoryBookingRepository
from infrastructure.workflows.activities import ConciergeActivities
from infrastructure.workflows.dtos import (
    BookingState,
    ForwardInput,
    HotelContactData,
    TopicData,
)

# --- fakes ---


class FakeExtractor:
    def __init__(self, extracted: ExtractedBooking) -> None:
        self._extracted = extracted

    async def extract(self, event: ConfirmForward) -> ExtractedBooking:
        return self._extracted


class FakeDiscoverer:
    def __init__(self, email: str | None, language: str = "en", found: bool = True) -> None:
        self._email = email
        self._language = language
        self._found = found

    async def discover(self, hotel_name: str, hint_website: str | None):
        from domain.intents import SearchDone

        return SearchDone(
            hotel_name=hotel_name,
            language=self._language,
            email=EmailAddress(self._email) if self._email else None,
            found=self._found,
        )


class FakeNegotiator:
    def __init__(self, intent: AgentIntent) -> None:
        self._intent = intent

    async def turn(self, booking_id: BookingId, trigger: object, booking: Booking) -> AgentIntent:
        return self._intent


class FakeReporter:
    async def build(self, booking: Booking) -> str:
        return "REPORT"


class FakeGateway:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []  # (booking_id, to, idempotency_key)

    async def send(self, *, booking_id, to, sender, reply_to, subject, body, idempotency_key):  # type: ignore[no-untyped-def]
        # second call with same key is a no-op (dedup), like the real gateway
        if any(k == idempotency_key for _, _, k in self.sent):
            return f"mg:{idempotency_key}"
        self.sent.append((booking_id, to.value, idempotency_key))
        return f"mg:{idempotency_key}"


class FakeNotifier:
    def __init__(self) -> None:
        self.notified: list[tuple[str, str, str, str]] = []  # (kind, booking_id, subject, body)

    async def notify(self, event) -> None:
        self.notified.append((event.kind, event.booking_id, event.subject, event.body))


def _extracted() -> ExtractedBooking:
    return ExtractedBooking(
        hotel_name="Grand",
        hotel_email=EmailAddress("stay@grand.com"),
        booking_ref="R1",
        check_in=date(2026, 2, 1),
        check_out=date(2026, 2, 4),
        guests=["Alice"],
        confidence=0.9,
    )


def _state() -> BookingState:
    return BookingState(
        booking_id="b1",
        client_token="tok",
        hotel=HotelContactData(hotel_name="Grand", email="hotel@grand.com"),
        booking_ref="R1",
        check_in="2026-02-01",
        check_out="2026-02-04",
        guests=["Alice"],
        topics=[
            TopicData(topic_id="b1:t:early-checkin", label="early-checkin"),
            TopicData(topic_id="b1:t:room-upgrade", label="room-upgrade"),
        ],
        lifecycle="in_conversation",
    )


def _activities(
    *,
    extractor: FakeExtractor | None = None,
    discoverer: FakeDiscoverer | None = None,
    negotiator: FakeNegotiator | None = None,
    reporter: FakeReporter | None = None,
    gateway: FakeGateway | None = None,
    notifier: FakeNotifier | None = None,
    bookings: InMemoryBookingRepository | None = None,
) -> tuple[ConciergeActivities, dict[str, object]]:
    fakes = {
        "extractor": extractor or FakeExtractor(_extracted()),
        "discoverer": discoverer or FakeDiscoverer("stay@grand.com"),
        "negotiator": negotiator or FakeNegotiator(SendEmail(to=EmailAddress("hotel@grand.com"), subject="S", body="B", language="en", topic_ids=[], step="initial")),
        "reporter": reporter or FakeReporter(),
        "gateway": gateway or FakeGateway(),
        "notifier": notifier or FakeNotifier(),
        "bookings": bookings or InMemoryBookingRepository(),
    }
    activities = ConciergeActivities(
        extractor=fakes["extractor"],  # type: ignore[arg-type]
        discoverer=fakes["discoverer"],  # type: ignore[arg-type]
        negotiator=fakes["negotiator"],  # type: ignore[arg-type]
        reporter=fakes["reporter"],  # type: ignore[arg-type]
        gateway=fakes["gateway"],  # type: ignore[arg-type]
        notifier=fakes["notifier"],  # type: ignore[arg-type]
        bookings=fakes["bookings"],  # type: ignore[arg-type]
        mail_domain="kkr-hotel.com",
    )
    return activities, fakes


def _forward() -> ForwardInput:
    return ForwardInput(
        client_token="tok",
        sender_email="client@example.com",
        subject="Fwd: booking",
        cover_text="get early check-in",
        forwarded_payload="confirmation body",
    )


class TestExtract:
    async def test_returns_extracted_data(self) -> None:
        activities, _ = _activities()
        data = await activities.extract(_forward())
        assert data.hotel_name == "Grand"
        assert data.hotel_email == "stay@grand.com"
        assert data.booking_ref == "R1"


class TestDiscoverContact:
    async def test_found(self) -> None:
        activities, _ = _activities(discoverer=FakeDiscoverer("r@grand.fr", language="fr"))
        result = await activities.discover_contact("Grand", None)
        assert result.found is True and result.email == "r@grand.fr" and result.language == "fr"

    async def test_not_found(self) -> None:
        activities, _ = _activities(discoverer=FakeDiscoverer(None, found=False))
        result = await activities.discover_contact("Grand", None)
        assert result.found is False


class TestAgentTurn:
    async def test_send_email_intent(self) -> None:
        intent = SendEmail(to=EmailAddress("hotel@grand.com"), subject="S", body="B", language="en", topic_ids=["b1:t:early-checkin"], step="initial")
        activities, _ = _activities(negotiator=FakeNegotiator(intent))
        result = await activities.agent_turn("b1", _state(), "compose_initial", "", None)
        assert result.action == "send_email"
        assert result.to == "hotel@grand.com" and result.step == "initial"

    async def test_resolved_intent(self) -> None:
        intent = Resolved(resolutions=[TopicResolution(topic_id="b1:t:early-checkin", status=TopicStatus.RESOLVED, result="granted")])
        activities, _ = _activities(negotiator=FakeNegotiator(intent))
        result = await activities.agent_turn("b1", _state(), "hotel_reply", "Yes", None)
        assert result.action == "resolved"
        assert result.resolutions[0].topic_id == "b1:t:early-checkin"


class TestSendEmail:
    async def test_sends_with_idempotency_key(self) -> None:
        activities, fakes = _activities()
        gateway: FakeGateway = fakes["gateway"]  # type: ignore[assignment]
        msg_id = await activities.send_email("b1", "hotel@grand.com", "Subject", "Body", "initial")
        assert msg_id == "mg:b1:initial"
        assert gateway.sent == [("b1", "hotel@grand.com", "b1:initial")]

    async def test_retry_does_not_duplicate(self) -> None:
        activities, fakes = _activities()
        gateway: FakeGateway = fakes["gateway"]  # type: ignore[assignment]
        await activities.send_email("b1", "hotel@grand.com", "Subject", "Body", "initial")
        await activities.send_email("b1", "hotel@grand.com", "Subject", "Body", "initial")
        assert len(gateway.sent) == 1


class TestBuildReport:
    async def test_returns_report(self) -> None:
        activities, _ = _activities()
        assert await activities.build_report(_state()) == "REPORT"


class TestRelayToClient:
    async def test_notifies_when_booking_exists(self) -> None:
        bookings = InMemoryBookingRepository()
        await bookings.save(Booking.start("b1", "tok", HotelContact(hotel_name="Grand", email=EmailAddress("h@x.com"))))
        activities, fakes = _activities(bookings=bookings)
        await activities.relay_to_client("b1", "Subject", "Body")
        notifier: FakeNotifier = fakes["notifier"]  # type: ignore[assignment]
        # relay_to_client delivers the report as a progress event (kind="report").
        assert notifier.notified == [("report", "b1", "Subject", "Body")]

    async def test_silent_when_booking_missing(self) -> None:
        activities, fakes = _activities()
        await activities.relay_to_client("missing", "S", "B")
        notifier: FakeNotifier = fakes["notifier"]  # type: ignore[assignment]
        assert notifier.notified == []


class TestNotifyProgress:
    async def test_pushes_progress_event_with_kind(self) -> None:
        bookings = InMemoryBookingRepository()
        await bookings.save(Booking.start("b1", "tok", HotelContact(hotel_name="Grand", email=EmailAddress("h@x.com"))))
        activities, fakes = _activities(bookings=bookings)
        await activities.notify_progress("b1", "sent", "Message sent", "I've sent the request.")
        notifier: FakeNotifier = fakes["notifier"]  # type: ignore[assignment]
        assert notifier.notified == [("sent", "b1", "Message sent", "I've sent the request.")]

    async def test_silent_when_booking_missing(self) -> None:
        activities, fakes = _activities()
        await activities.notify_progress("missing", "sent", "S", "B")
        notifier: FakeNotifier = fakes["notifier"]  # type: ignore[assignment]
        assert notifier.notified == []


class TestUpdateBookingState:
    async def test_persists_booking(self) -> None:
        bookings = InMemoryBookingRepository()
        activities, _ = _activities(bookings=bookings)
        await activities.update_booking_state(_state())
        loaded = await bookings.get("b1")
        assert loaded is not None and loaded.hotel.hotel_name == "Grand"


class TestRecordInboundReply:
    async def test_records_message(self) -> None:
        bookings = InMemoryBookingRepository()
        activities, _ = _activities(bookings=bookings)
        await activities.record_inbound_reply("b1", "hotel@grand.com", "Re:", "Yes", "hotel")
        msgs = await bookings.messages("b1")
        assert len(msgs) == 1 and msgs[0].body == "Yes"
