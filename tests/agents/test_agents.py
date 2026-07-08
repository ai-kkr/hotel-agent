from __future__ import annotations

from datetime import UTC, datetime

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from domain.entities import Booking, HotelContact
from domain.events import ConfirmForward
from domain.ids import EmailAddress
from domain.intents import ComposeInitial, NeedMoreInfo, ParseHotelReply, Resolved, SendEmail
from infrastructure.agents.discoverer import ContactDiscovererAgent
from infrastructure.agents.extractor import ConfirmationExtractorAgent
from infrastructure.agents.negotiator import NegotiationAgentImpl
from infrastructure.agents.reporter import ReportBuilderAgent
from infrastructure.agents.schemas import (
    ExtractedBookingSchema,
)
from infrastructure.agents.tools import FakeWebFetcher, FakeWebSearcher, SearchResult
from infrastructure.db.langgraph import thread_config
from tests.agents.fakes import FakeChatModel, tool_call


def _forward(payload: str = "confirmation body", cover: str = "Fwd: booking") -> ConfirmForward:
    return ConfirmForward(
        client_token="tok",
        sender_email=EmailAddress("client@example.com"),
        subject="Fwd: booking",
        cover_text=cover,
        forwarded_payload=payload,
        received_at=datetime.now(tz=UTC),
    )


def _booking() -> Booking:
    b = Booking.start(
        booking_id="b1",
        client_token="tok",
        hotel=HotelContact(hotel_name="Grand", email=EmailAddress("hotel@grand.com")),
        language="en",
    )
    b.booking_ref = "R1"
    return b


# --------------------------------------------------------------------------- extractor


class TestConfirmationExtractor:
    async def test_full_confident_extraction(self) -> None:
        schema = ExtractedBookingSchema(
            hotel_name="Grand",
            hotel_email="stay@grand.com",
            booking_ref="R1",
            check_in="2026-02-01",
            check_out="2026-02-04",
            guests=["Alice"],
            wishes=["high floor"],
            confidence=0.9,
        )
        agent = ConfirmationExtractorAgent(FakeChatModel().with_structured(schema), confidence_threshold=0.7)
        eb = await agent.extract(_forward())
        assert eb.hotel_name == "Grand"
        assert eb.hotel_email is not None and eb.hotel_email.value == "stay@grand.com"
        assert eb.wishes == ["high floor"]
        assert eb.is_confident is True
        assert eb.missing_required == []

    async def test_low_confidence_flag(self) -> None:
        schema = ExtractedBookingSchema(
            hotel_name="Grand", booking_ref="R1", check_in="2026-02-01", check_out="2026-02-04", confidence=0.3
        )
        agent = ConfirmationExtractorAgent(FakeChatModel().with_structured(schema), confidence_threshold=0.7)
        eb = await agent.extract(_forward())
        assert eb.low_confidence is True
        assert eb.is_confident is False

    async def test_missing_required_field(self) -> None:
        schema = ExtractedBookingSchema(
            hotel_name="Grand", check_in="2026-02-01", check_out="2026-02-04", confidence=0.9
        )
        agent = ConfirmationExtractorAgent(FakeChatModel().with_structured(schema), confidence_threshold=0.7)
        eb = await agent.extract(_forward())
        assert "booking_ref" in eb.missing_required
        assert eb.is_confident is False


# --------------------------------------------------------------------------- discoverer


class TestContactDiscoverer:
    async def test_finds_contact_and_language(self) -> None:
        model = FakeChatModel().with_response(
            tool_call("ContactSchema", {"email": "stay@grand.fr", "language": "fr", "website": "https://grand.fr", "found": True})
        )
        agent = ContactDiscovererAgent(model, FakeWebSearcher(), FakeWebFetcher())
        result = await agent.discover("Grand Hotel", "https://grand.fr")
        assert result.found is True
        assert result.email is not None and result.email.value == "stay@grand.fr"
        assert result.language == "fr"

    async def test_falls_back_to_english_when_not_found(self) -> None:
        model = FakeChatModel().with_response(tool_call("ContactSchema", {"found": False}))
        agent = ContactDiscovererAgent(model, FakeWebSearcher(), FakeWebFetcher())
        result = await agent.discover("Unknown Hotel", None)
        assert result.found is False
        assert result.email is None
        assert result.language == "en"

    async def test_uses_web_search_in_loop(self) -> None:
        searcher = FakeWebSearcher().add(
            "Grand contact email", [SearchResult("Grand", "https://grand.com", "reception@grand.com")]
        )
        model = FakeChatModel().with_response(
            tool_call("web_search", {"query": "Grand contact email"})
        ).with_response(tool_call("ContactSchema", {"email": "reception@grand.com", "language": "en", "found": True}))
        agent = ContactDiscovererAgent(model, searcher, FakeWebFetcher())
        result = await agent.discover("Grand", None)
        assert result.found is True
        assert searcher.queries == ["Grand contact email"]


# --------------------------------------------------------------------------- negotiator


class TestNegotiationAgent:
    @pytest.fixture
    def checkpointer(self) -> InMemorySaver:
        return InMemorySaver()

    async def test_compose_initial_emits_send_email(self, checkpointer: InMemorySaver) -> None:
        model = FakeChatModel().with_response(
            tool_call(
                "IntentSchema",
                {
                    "action": "send_email",
                    "to": "hotel@grand.com",
                    "subject": "Request",
                    "body": "Hello",
                    "language": "en",
                    "topics": ["early-checkin", "room-upgrade"],
                    "step": "initial",
                },
            )
        )
        agent = NegotiationAgentImpl(model, FakeWebSearcher(), FakeWebFetcher(), checkpointer)
        intent = await agent.turn("b1", ComposeInitial(), _booking())
        assert isinstance(intent, SendEmail)
        assert intent.to.value == "hotel@grand.com"
        assert intent.step == "initial"
        assert intent.topic_ids == ["b1:t:early-checkin", "b1:t:room-upgrade"]

    async def test_resolved_maps_resolutions(self, checkpointer: InMemorySaver) -> None:
        model = FakeChatModel().with_response(
            tool_call(
                "IntentSchema",
                {
                    "action": "resolved",
                    "resolutions": [
                        {"topic_id": "b1:t:early-checkin", "status": "resolved", "result": "granted at 10am"},
                        {"topic_id": "b1:t:room-upgrade", "status": "unresolved", "result": "no answer"},
                    ],
                },
            )
        )
        agent = NegotiationAgentImpl(model, FakeWebSearcher(), FakeWebFetcher(), checkpointer)
        intent = await agent.turn("b1", ParseHotelReply(body="Yes early ok"), _booking())
        assert isinstance(intent, Resolved)
        assert len(intent.resolutions) == 2
        assert intent.resolutions[0].status.value == "resolved"

    async def test_need_more_info(self, checkpointer: InMemorySaver) -> None:
        model = FakeChatModel().with_response(
            tool_call("IntentSchema", {"action": "need_more_info", "reason": "ambiguous dates", "question_to_client": "Which dates?"})
        )
        agent = NegotiationAgentImpl(model, FakeWebSearcher(), FakeWebFetcher(), checkpointer)
        intent = await agent.turn("b1", ParseHotelReply(body="maybe"), _booking())
        assert isinstance(intent, NeedMoreInfo)
        assert intent.question_to_client == "Which dates?"

    async def test_no_structured_response_falls_back(self, checkpointer: InMemorySaver) -> None:
        from langchain_core.messages import AIMessage

        model = FakeChatModel().with_response(AIMessage(content="I'm not sure"))
        agent = NegotiationAgentImpl(model, FakeWebSearcher(), FakeWebFetcher(), checkpointer)
        intent = await agent.turn("b1", ComposeInitial(), _booking())
        assert isinstance(intent, NeedMoreInfo)

    async def test_context_persists_on_checkpointer(self, checkpointer: InMemorySaver) -> None:
        model = FakeChatModel().with_response(
            tool_call("IntentSchema", {"action": "need_more_info", "reason": "x", "question_to_client": "y"})
        )
        agent = NegotiationAgentImpl(model, FakeWebSearcher(), FakeWebFetcher(), checkpointer)
        await agent.turn("b1", ComposeInitial(), _booking())
        checkpoint = await checkpointer.aget(thread_config("b1"))
        assert checkpoint is not None  # per-booking thread_id = booking_id


# --------------------------------------------------------------------------- reporter


class TestReportBuilder:
    async def test_builds_report_text(self) -> None:
        from langchain_core.messages import AIMessage

        model = FakeChatModel().with_response(AIMessage(content="Hi! Early check-in granted."))
        agent = ReportBuilderAgent(model)
        report = await agent.build(_booking())
        assert "Early check-in granted" in report
