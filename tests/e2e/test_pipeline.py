"""End-to-end pipeline tests (spec 9.1-9.5).

These drive the same activity + decision sequence the ``BookingWorkflow`` drives, offline, with
scripted agents and fakes. They validate the integrated pipeline (extract → discover → negotiate →
send → report). The Temporal workflow execution itself is covered by the gated E2E test in Group 6.
"""

from __future__ import annotations

from datetime import date

import httpx
import respx

from domain.entities import Booking
from domain.enums import TopicStatus
from domain.extraction import ExtractedBooking
from domain.ids import EmailAddress
from domain.intents import (
    AgentIntent,
    ComposeInitial,
    NeedMoreInfo,
    ParseHotelReply,
    Resolved,
    SendEmail,
    TopicResolution,
)
from infrastructure.mail.mailgun import MailgunOutboundGateway
from infrastructure.persistence.in_memory import InMemoryBookingRepository
from infrastructure.workflows import decisions as d
from infrastructure.workflows.activities import ConciergeActivities
from infrastructure.workflows.dtos import ForwardInput
from tests.workflows.test_activities import (
    FakeDiscoverer,
    FakeExtractor,
    FakeGateway,
    FakeNotifier,
    FakeReporter,
)


class ScriptedNegotiator:
    """Returns a scripted intent per trigger kind."""

    def __init__(self, by_trigger: dict[str, AgentIntent]) -> None:
        self._by_trigger = by_trigger

    async def turn(self, booking_id: str, trigger: object, booking: Booking) -> AgentIntent:
        from domain.intents import ClientFollowup, TimeoutFollowup

        match trigger:
            case ComposeInitial():
                key = "compose_initial"
            case ParseHotelReply():
                key = "hotel_reply"
            case ClientFollowup():
                key = "client_followup"
            case TimeoutFollowup():
                key = "timeout_followup"
            case _:
                key = "compose_initial"
        return self._by_trigger.get(key, NeedMoreInfo(reason="unhandled", question_to_client=""))


def _forward() -> ForwardInput:
    return ForwardInput(
        client_token="tok",
        sender_email="client@example.com",
        subject="Fwd: booking",
        cover_text="please get early check-in",
        forwarded_payload="confirmation body",
    )


def _extracted(hotel_email: str | None = "stay@grand.com") -> ExtractedBooking:
    return ExtractedBooking(
        hotel_name="Grand",
        hotel_email=EmailAddress(hotel_email) if hotel_email else None,
        booking_ref="R1",
        check_in=date(2026, 2, 1),
        check_out=date(2026, 2, 4),
        guests=["Alice"],
        confidence=0.9,
    )


def _activities(
    *,
    extracted: ExtractedBooking | None = None,
    discoverer: FakeDiscoverer | None = None,
    negotiator: ScriptedNegotiator | None = None,
    gateway: FakeGateway | None = None,
    notifier: FakeNotifier | None = None,
) -> tuple[ConciergeActivities, dict[str, object]]:
    bookings = InMemoryBookingRepository()
    fakes = {
        "bookings": bookings,
        "gateway": gateway or FakeGateway(),
        "notifier": notifier or FakeNotifier(),
    }
    activities = ConciergeActivities(
        extractor=FakeExtractor(extracted or _extracted()),
        discoverer=discoverer or FakeDiscoverer("stay@grand.com"),
        negotiator=negotiator or ScriptedNegotiator({}),
        reporter=FakeReporter(),
        gateway=fakes["gateway"],  # type: ignore[arg-type]
        notifier=fakes["notifier"],  # type: ignore[arg-type]
        bookings=bookings,
        mail_domain="kkr-hotel.com",
    )
    return activities, fakes


# --- 9.1 forward → negotiate → report ---


class TestForwardToReport:
    async def test_full_pipeline_delivers_report(self) -> None:
        resolved = Resolved(
            resolutions=[
                TopicResolution(topic_id="wt:t:early-checkin", status=TopicStatus.RESOLVED, result="granted"),
                TopicResolution(topic_id="wt:t:room-upgrade", status=TopicStatus.RESOLVED, result="offered 40 eur"),
            ]
        )
        negotiator = ScriptedNegotiator(
            {
                "compose_initial": SendEmail(
                    to=EmailAddress("stay@grand.com"),
                    subject="Request",
                    body="Hello",
                    language="en",
                    topic_ids=["wt:t:early-checkin", "wt:t:room-upgrade"],
                    step="initial",
                ),
                "hotel_reply": resolved,
            }
        )
        activities, fakes = _activities(negotiator=negotiator)
        gateway: FakeGateway = fakes["gateway"]  # type: ignore[assignment]
        notifier: FakeNotifier = fakes["notifier"]  # type: ignore[assignment]

        extracted = await activities.extract(_forward())
        state = d.state_from_extraction("wt", "tok", extracted)
        await activities.update_booking_state(state)

        # compose + send
        intent = await activities.agent_turn("wt", state, "compose_initial", "", None)
        await activities.send_email("wt", intent.to, intent.subject, intent.body, intent.step)  # type: ignore[arg-type]
        state = d.record_email_sent(state, intent.step)

        # hotel reply → resolved
        resolved_intent = await activities.agent_turn("wt", state, "hotel_reply", "Yes", None)
        state = d.apply_resolutions(state, resolved_intent.resolutions)  # type: ignore[attr-defined]
        await activities.update_booking_state(state)
        assert d.should_build_report(state)

        # report
        report = await activities.build_report(state)
        await activities.relay_to_client("wt", "Your report", report)

        assert len(gateway.sent) == 1 and gateway.sent[0][1] == "stay@grand.com"  # type: ignore[index]
        assert any(kind == "report" and "report" in subject.lower() for kind, _bid, subject, _body in notifier.notified)
        bookings: InMemoryBookingRepository = fakes["bookings"]  # type: ignore[assignment]
        saved = await bookings.get("wt")
        assert saved is not None and all(t.status is TopicStatus.RESOLVED for t in saved.topics)


# --- 9.2 client follow-up → re-engage hotel ---


class TestClientFollowupReengages:
    async def test_second_email_after_followup(self) -> None:
        resolved = Resolved(resolutions=[
            TopicResolution(topic_id="wt:t:early-checkin", status=TopicStatus.RESOLVED, result="granted"),
            TopicResolution(topic_id="wt:t:room-upgrade", status=TopicStatus.RESOLVED, result="ok"),
        ])
        negotiator = ScriptedNegotiator(
            {
                "compose_initial": SendEmail(to=EmailAddress("stay@grand.com"), subject="R", body="B", language="en", topic_ids=[], step="initial"),
                "hotel_reply": resolved,
                "client_followup": SendEmail(to=EmailAddress("stay@grand.com"), subject="Late checkout", body="B2", language="en", topic_ids=[], step="followup1"),
            }
        )
        activities, fakes = _activities(negotiator=negotiator)
        gateway: FakeGateway = fakes["gateway"]  # type: ignore[assignment]

        extracted = await activities.extract(_forward())
        state = d.state_from_extraction("wt", "tok", extracted)
        # resolve initial topics
        intent = await activities.agent_turn("wt", state, "compose_initial", "", None)
        await activities.send_email("wt", intent.to, intent.subject, intent.body, intent.step)  # type: ignore[arg-type]
        state = d.record_email_sent(state, intent.step)
        r = await activities.agent_turn("wt", state, "hotel_reply", "Yes", None)
        state = d.apply_resolutions(state, r.resolutions)  # type: ignore[attr-defined]

        # client follow-up reactivates → second email
        state = d.add_client_followup_topics(state, ["late-checkout"])
        followup = await activities.agent_turn("wt", state, "client_followup", "also late checkout please", None)
        await activities.send_email("wt", followup.to, followup.subject, followup.body, followup.step)  # type: ignore[arg-type]

        steps = {s[2] for s in gateway.sent}  # type: ignore[index]
        assert steps == {"wt:initial", "wt:followup1"}


# --- 9.3 discovery via web (mocked search) ---


class TestContactDiscoveryViaWeb:
    async def test_forward_without_hotel_email_discovers_contact(self) -> None:
        discoverer = FakeDiscoverer("discovered@grand.com", language="fr")
        activities, _ = _activities(extracted=_extracted(hotel_email=None), discoverer=discoverer)
        extracted = await activities.extract(_forward())
        assert extracted.hotel_email is None
        state = d.state_from_extraction("wt", "tok", extracted)
        assert state.needs_discovery is True

        contact = await activities.discover_contact(state.hotel.hotel_name, state.hotel.website)
        state = d.apply_contact(state, contact)
        assert state.lifecycle == "contact_ready"
        assert state.hotel.email == "discovered@grand.com"
        assert state.language == "fr"


# --- 9.4 idempotent send under activity retry ---


class TestIdempotentSendUnderRetry:
    @respx.mock
    async def test_real_gateway_sends_once_under_retry(self) -> None:
        route = respx.post("https://api.mailgun.net/v3/kkr-hotel.com/messages").mock(
            return_value=httpx.Response(200, json={"id": "<1>"})
        )
        bookings = InMemoryBookingRepository()
        gateway = MailgunOutboundGateway(
            api_key="key",
            base_url="https://api.mailgun.net",
            mail_domain="kkr-hotel.com",
            repo=bookings,
        )
        activities = ConciergeActivities(
            extractor=FakeExtractor(_extracted()),
            discoverer=FakeDiscoverer("stay@grand.com"),
            negotiator=ScriptedNegotiator({}),
            reporter=FakeReporter(),
            gateway=gateway,
            notifier=FakeNotifier(),
            bookings=bookings,
            mail_domain="kkr-hotel.com",
        )
        first = await activities.send_email("b1", "stay@grand.com", "S", "B", "initial")
        second = await activities.send_email("b1", "stay@grand.com", "S", "B", "initial")  # retry
        assert first == second == "mg:b1:initial"
        assert route.call_count == 1  # no duplicate email


# --- 9.5 hotel language + English fallback ---


class TestHotelLanguageAndFallback:
    async def test_language_from_discovery(self) -> None:
        discoverer = FakeDiscoverer("stay@grand.es", language="es")
        activities, _ = _activities(extracted=_extracted(hotel_email=None), discoverer=discoverer)
        contact = await activities.discover_contact("Grand", None)
        assert contact.language == "es"

    async def test_english_fallback_when_not_found(self) -> None:
        activities, _ = _activities(extracted=_extracted(hotel_email=None), discoverer=FakeDiscoverer(None, found=False))
        contact = await activities.discover_contact("Unknown", None)
        assert contact.found is False
        assert contact.language == "en"
