from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from domain.application import ChatIntakeService, MailboxService
from domain.entities import Booking, HotelContact
from domain.enums import Channel
from domain.ids import EmailAddress
from domain.intents import CancelBooking
from infrastructure.agents.surface import SurfaceAgent, SurfaceDeps
from infrastructure.agents.tools import FakeWebFetcher, FakeWebSearcher
from infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryChannelSessionRepository,
    InMemoryClientRepository,
)
from tests.agents.fakes import FakeChatModel, tool_call


async def _deps(
    bookings: InMemoryBookingRepository | None = None,
) -> tuple[SurfaceDeps, InMemoryChannelSessionRepository, InMemoryBookingRepository, InMemoryClientRepository]:
    clients = InMemoryClientRepository()
    sessions = InMemoryChannelSessionRepository()
    bookings = bookings or InMemoryBookingRepository()
    mailbox = MailboxService(
        clients=clients, sessions=sessions, mail_domain="kkr-hotel.com", token_factory=lambda: "tok"
    )
    # Pre-bind a chat so list_tasks/delete_task have a client.
    await mailbox.resolve_or_create(Channel.TELEGRAM, "chat:1")
    intake = ChatIntakeService(sessions=sessions, clients=clients, gateway=_NullGateway())
    return (
        SurfaceDeps(mailbox=mailbox, sessions=sessions, bookings=bookings, intake=intake),
        sessions,
        bookings,
        clients,
    )


class _NullGateway:
    async def start_booking(self, event: object) -> None: ...
    async def signal_hotel_reply(self, event: object) -> None: ...
    async def signal_client_message(self, event: object) -> None: ...
    async def signal_delivery_failure(self, *args: object) -> None: ...


class _RecordingGateway(_NullGateway):
    def __init__(self) -> None:
        self.started: list[object] = []

    async def start_booking(self, event: object) -> None:
        self.started.append(event)


def _agent(model: FakeChatModel, deps: SurfaceDeps) -> SurfaceAgent:
    return SurfaceAgent(
        model=model,
        searcher=FakeWebSearcher(),
        fetcher=FakeWebFetcher(),
        checkpointer=InMemorySaver(),
        deps=deps,
    )


class TestSurfaceAgent:
    async def test_delete_task_emits_cancel_intent_no_side_effect(self) -> None:
        deps, _sessions, bookings, _clients = await _deps()
        await bookings.save(
            Booking.start(
                booking_id="b1",
                client_token="tok",
                hotel=HotelContact(hotel_name="Grand", email=EmailAddress("hotel@grand.com")),
            )
        )
        model = FakeChatModel().with_response(
            tool_call("delete_task", {"booking_id": "b1"})
        ).with_response(AIMessage(content="I'll cancel that for you."))
        agent = _agent(model, deps)
        reply = await agent.converse("chat:1", "cancel my booking")
        assert any(isinstance(a, CancelBooking) and a.booking_id == "b1" for a in reply.artifacts)
        # No side-effect: the booking is NOT cancelled by the agent.
        booking = await bookings.get("b1")
        assert booking is not None and not booking.is_cancelled

    async def test_ask_user_presents_free_text_hints_no_artifact(self) -> None:
        # ask_user no longer emits a RequestUserDecision artifact; it returns free-text hints that
        # the agent folds into its reply. The guest may then answer freely (incl. multi-select).
        deps, _s, _b, _c = await _deps()
        model = FakeChatModel().with_response(
            tool_call("ask_user", {"question": "Early check-in?", "options": ["Yes", "No"]})
        ).with_response(AIMessage(content="Early check-in? Options: Yes, No"))
        agent = _agent(model, deps)
        reply = await agent.converse("chat:1", "what can you do")
        # No structured-decision artifact is emitted (free-text surface).
        assert not any(isinstance(a, CancelBooking) for a in reply.artifacts)
        # The agent surfaces the options as hints in its text reply.
        assert "Yes" in reply.text and "No" in reply.text

    async def test_intake_delegates_to_core(self) -> None:
        deps, _s, _b, _c = await _deps()
        agent = _agent(FakeChatModel(), deps)
        reply = await agent.intake_forward(
            "chat:1", "confirmation body", "please early check-in", datetime.now(tz=UTC)
        )
        # chat:1 has a session → intake should start (NullGateway swallows the start).
        assert reply.client_token == "tok"
        assert "concierge" in reply.text.lower()

    async def test_intake_unknown_session_prompts_mailbox(self) -> None:
        deps, _s, _b, _c = await _deps()
        agent = _agent(FakeChatModel(), deps)
        reply = await agent.intake_forward(
            "no-such-chat", "confirmation body", "", datetime.now(tz=UTC)
        )
        assert reply.client_token is None
        assert "mailbox" in reply.text.lower()

    async def test_general_question_uses_text_only(self) -> None:
        deps, _s, _b, _c = await _deps()
        model = FakeChatModel().with_response(AIMessage(content="The gym is open 6am-10pm."))
        agent = _agent(model, deps)
        reply = await agent.converse("chat:1", "what time is the gym open?")
        assert reply.text == "The gym is open 6am-10pm."
        assert reply.artifacts == []

    async def test_forward_confirmation_calls_intake_start(self) -> None:
        # forward_confirmation is the only path a chat booking reaches the core intake → workflow.
        # Without it the agent can only hallucinate "sent"; this pins that the tool really starts intake.
        clients = InMemoryClientRepository()
        sessions = InMemoryChannelSessionRepository()
        mailbox = MailboxService(
            clients=clients, sessions=sessions, mail_domain="kkr-hotel.com", token_factory=lambda: "tok"
        )
        await mailbox.resolve_or_create(Channel.TELEGRAM, "chat:1")
        gateway = _RecordingGateway()
        intake = ChatIntakeService(sessions=sessions, clients=clients, gateway=gateway)
        deps = SurfaceDeps(
            mailbox=mailbox, sessions=sessions, bookings=InMemoryBookingRepository(), intake=intake
        )
        model = (
            FakeChatModel()
            .with_response(
                tool_call(
                    "forward_confirmation",
                    {"payload": "Booking ref ABC, Dobedan, 29.04.2025", "wishes": "early check-in"},
                )
            )
            .with_response(AIMessage(content="Sent to the concierge."))
        )
        agent = _agent(model, deps)
        await agent.converse("chat:1", "here is my booking: Booking ref ABC, Dobedan")
        assert len(gateway.started) == 1


class TestNoTelegramImports:
    def test_surface_agent_does_not_import_telegram(self) -> None:
        import ast
        import inspect

        from infrastructure.agents import surface

        tree = ast.parse(inspect.getsource(surface))
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "telegram" not in imported, (
            f"surface agent layer must not import telegram (found: {sorted(imported)})"
        )
