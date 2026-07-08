"""Temporal activities (spec 6.2).

ALL LLM calls and side-effects (mail sending, persistence) live here — never in workflow code
(design D2). Activities receive collaborators via the ``ConciergeActivities`` instance and exchange
serializable DTOs with the workflow.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from temporalio import activity

from domain.entities import Booking, HotelContact, Message, Topic
from domain.enums import (
    BookingLifecycle,
    Channel,
    MessageDirection,
    SenderRole,
    TopicStatus,
)
from domain.events import ConfirmForward
from domain.ids import BookingId, EmailAddress, conversation_address
from domain.intents import (
    AgentIntent,
    ClientFollowup,
    ComposeInitial,
    NeedMoreInfo,
    ParseHotelReply,
    Resolved,
    SearchDone,
    SendEmail,
    TimeoutFollowup,
)
from domain.ports import (
    BookingRepository,
    ClientNotifier,
    ConfirmationExtractor,
    ContactDiscoverer,
    NegotiationAgent,
    OutboundMailGateway,
    ReportBuilder,
)
from infrastructure.workflows.dtos import (
    BookingState,
    ContactResult,
    ExtractedData,
    ForwardInput,
    IntentResult,
    ResolutionData,
)


def _state_to_booking(state: BookingState) -> Booking:
    hotel = HotelContact(
        hotel_name=state.hotel.hotel_name,
        email=EmailAddress(state.hotel.email) if state.hotel.email else None,
        website=state.hotel.website,
        language=state.hotel.language,
        discovered=state.hotel.discovered,
    )
    booking = Booking(
        booking_id=state.booking_id,
        client_token=state.client_token,
        hotel=hotel,
        booking_ref=state.booking_ref,
        check_in=date.fromisoformat(state.check_in) if state.check_in else None,
        check_out=date.fromisoformat(state.check_out) if state.check_out else None,
        guests=list(state.guests),
        room_type=state.room_type,
        language=state.language,
        wishes=list(state.wishes),
        lifecycle=BookingLifecycle(state.lifecycle),
        followup_attempts=state.followup_attempts,
    )
    booking.topics = [
        Topic(topic_id=t.topic_id, label=t.label, status=TopicStatus(t.status), result=t.result)
        for t in state.topics
    ]
    return booking


def _trigger(kind: str, body: str, subject: str | None):
    match kind:
        case "compose_initial":
            return ComposeInitial()
        case "hotel_reply":
            return ParseHotelReply(body=body, subject=subject)
        case "client_followup":
            return ClientFollowup(body=body)
        case "timeout_followup":
            return TimeoutFollowup()
        case _:
            return ComposeInitial()


def _intent_to_result(intent: AgentIntent) -> IntentResult:
    match intent:
        case SendEmail(
            to=to, subject=subject, body=body, language=language, topic_ids=topics, step=step
        ):
            return IntentResult(
                action="send_email",
                to=to.value,
                subject=subject,
                body=body,
                language=language,
                topics=list(topics),
                step=step,
            )
        case Resolved(resolutions=resolutions):
            return IntentResult(
                action="resolved",
                resolutions=[
                    ResolutionData(topic_id=r.topic_id, status=r.status.value, result=r.result)
                    for r in resolutions
                ],
            )
        case NeedMoreInfo(reason=reason, question_to_client=question):
            return IntentResult(action="need_more_info", reason=reason, question_to_client=question)
        case SearchDone():
            return IntentResult(action="need_more_info", reason="discovery incomplete")
        case _:  # pragma: no cover - defensive
            return IntentResult(action="need_more_info", reason="unhandled intent")


class ConciergeActivities:
    """Activity implementation holding all collaborators."""

    def __init__(
        self,
        *,
        extractor: ConfirmationExtractor,
        discoverer: ContactDiscoverer,
        negotiator: NegotiationAgent,
        reporter: ReportBuilder,
        gateway: OutboundMailGateway,
        notifier: ClientNotifier,
        bookings: BookingRepository,
        mail_domain: str,
    ) -> None:
        self._extractor = extractor
        self._discoverer = discoverer
        self._negotiator = negotiator
        self._reporter = reporter
        self._gateway = gateway
        self._notifier = notifier
        self._bookings = bookings
        self._mail_domain = mail_domain

    @activity.defn
    async def extract(self, forward: ForwardInput) -> ExtractedData:
        event = ConfirmForward(
            client_token=forward.client_token,
            sender_email=EmailAddress(forward.sender_email),
            subject=forward.subject,
            cover_text=forward.cover_text,
            forwarded_payload=forward.forwarded_payload,
            received_at=datetime.now(tz=UTC),
        )
        extracted = await self._extractor.extract(event)
        return ExtractedData(
            hotel_name=extracted.hotel_name,
            hotel_email=extracted.hotel_email.value if extracted.hotel_email else None,
            hotel_website=extracted.hotel_website,
            booking_ref=extracted.booking_ref,
            check_in=extracted.check_in.isoformat() if extracted.check_in else None,
            check_out=extracted.check_out.isoformat() if extracted.check_out else None,
            guests=list(extracted.guests),
            room_type=extracted.room_type,
            wishes=list(extracted.wishes),
            confidence=extracted.confidence,
            missing_required=list(extracted.missing_required),
            low_confidence=extracted.low_confidence,
        )

    @activity.defn
    async def discover_contact(self, hotel_name: str, hint_website: str | None) -> ContactResult:
        result = await self._discoverer.discover(hotel_name, hint_website)
        return ContactResult(
            email=result.email.value if result.email else None,
            language=result.language,
            website=result.website,
            found=result.found,
        )

    @activity.defn
    async def agent_turn(
        self, booking_id: str, state: BookingState, trigger_kind: str, trigger_body: str, trigger_subject: str | None
    ) -> IntentResult:
        booking = _state_to_booking(state)
        intent = await self._negotiator.turn(
            BookingId(booking_id), _trigger(trigger_kind, trigger_body, trigger_subject), booking
        )
        return _intent_to_result(intent)

    @activity.defn
    async def send_email(
        self, booking_id: str, to: str, subject: str, body: str, step: str
    ) -> str:
        sender = conversation_address(booking_id, self._mail_domain)
        message_id = await self._gateway.send(
            booking_id=BookingId(booking_id),
            to=EmailAddress(to),
            sender=sender,
            reply_to=sender,
            subject=subject,
            body=body,
            idempotency_key=f"{booking_id}:{step}",
        )
        return message_id

    @activity.defn
    async def build_report(self, state: BookingState) -> str:
        return await self._reporter.build(_state_to_booking(state))

    @activity.defn
    async def relay_to_client(self, booking_id: str, subject: str, body: str) -> None:
        booking = await self._bookings.get(BookingId(booking_id))
        if booking is None:
            return
        await self._notifier.notify(booking, subject, body)

    @activity.defn
    async def update_booking_state(self, state: BookingState) -> None:
        await self._bookings.save(_state_to_booking(state))

    @activity.defn
    async def record_inbound_reply(
        self, booking_id: str, from_email: str, subject: str | None, body: str, role: str
    ) -> None:
        """Persist an inbound hotel/client message (audit trail)."""
        message = Message(
            message_id=f"in:{booking_id}:{datetime.now(tz=UTC).timestamp()}",
            booking_id=BookingId(booking_id),
            direction=MessageDirection.INBOUND,
            channel=Channel.EMAIL,
            subject=subject,
            body=body,
            sender=EmailAddress(from_email),
            sender_role=SenderRole(role),
            created_at=datetime.now(tz=UTC),
        )
        await self._bookings.add_message(message)
