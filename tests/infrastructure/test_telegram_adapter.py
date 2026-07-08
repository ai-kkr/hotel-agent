from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from tests.agents.fakes import FakeChatModel, tool_call

from domain.application import ChatIntakeService, MailboxService
from domain.enums import Channel
from domain.intents import RequestUserDecision
from domain.ports import ProgressEvent
from infrastructure.agents.surface import SurfaceAgent, SurfaceDeps, SurfaceReply
from infrastructure.agents.tools import FakeWebFetcher, FakeWebSearcher
from infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryChannelSessionRepository,
    InMemoryClientRepository,
)
from infrastructure.telegram.adapter import (
    TelegramAdapter,
    TelegramClientNotifier,
    normalize_callback,
    render_inline_keyboard,
    render_reply,
)


@dataclass
class RecordingBot:
    sent: list[tuple[str, str, dict[str, Any] | None]] = field(default_factory=list)
    answered: list[str] = field(default_factory=list)

    async def send_message(
        self, chat_id: str, text: str, reply_markup: dict[str, Any] | None = None
    ) -> None:
        self.sent.append((chat_id, text, reply_markup))

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        self.answered.append(callback_query_id)


def _decision() -> RequestUserDecision:
    return RequestUserDecision(question="Early check-in?", options=["Yes", "No"])


class TestRendering:
    def test_inline_keyboard_has_one_row_per_decision(self) -> None:
        markup = render_inline_keyboard(_decision())
        assert len(markup["inline_keyboard"]) == 1
        labels = [b["text"] for b in markup["inline_keyboard"][0]]
        assert labels == ["Yes", "No"]

    def test_render_reply_includes_question_and_markup(self) -> None:
        reply = SurfaceReply(text="Sure.", artifacts=[_decision()])
        text, markup = render_reply(reply)
        assert "Early check-in?" in text
        assert "Sure." in text
        assert markup is not None and "inline_keyboard" in markup

    def test_render_reply_without_artifact_has_no_markup(self) -> None:
        text, markup = render_reply(SurfaceReply(text="hi"))
        assert text == "hi"
        assert markup is None


class TestCallbackNormalization:
    def test_round_trip_option(self) -> None:
        markup = render_inline_keyboard(_decision())
        data = markup["inline_keyboard"][0][0]["callback_data"]
        assert normalize_callback(data) == "Yes"


async def _make_adapter(model: FakeChatModel) -> tuple[TelegramAdapter, RecordingBot, InMemoryChannelSessionRepository]:
    bot = RecordingBot()
    clients = InMemoryClientRepository()
    sessions = InMemoryChannelSessionRepository()
    mailbox = MailboxService(
        clients=clients, sessions=sessions, mail_domain="kkr-hotel.com", token_factory=lambda: "tok"
    )
    intake = ChatIntakeService(sessions=sessions, clients=clients, gateway=_NullGateway())
    deps = SurfaceDeps(
        mailbox=mailbox, sessions=sessions, bookings=InMemoryBookingRepository(), intake=intake
    )
    agent = SurfaceAgent(model, FakeWebSearcher(), FakeWebFetcher(), InMemorySaver(), deps)
    return TelegramAdapter(bot=bot, agent=agent, sessions=sessions, mailbox=mailbox), bot, sessions


class _NullGateway:
    async def start_booking(self, event: object) -> None: ...
    async def signal_hotel_reply(self, event: object) -> None: ...
    async def signal_client_message(self, event: object) -> None: ...
    async def signal_delivery_failure(self, *args: object) -> None: ...


class TestRouting:
    async def test_inbound_sends_text(self) -> None:
        model = FakeChatModel().with_response(AIMessage(content="Hello there."))
        adapter, bot, _sessions = await _make_adapter(model)
        await adapter.handle_inbound("chat:1", "hi")
        assert len(bot.sent) == 1
        assert bot.sent[0][0] == "chat:1"
        assert bot.sent[0][1] == "Hello there."
        assert bot.sent[0][2] is None  # no markup for a plain reply

    async def test_inbound_renders_keyboard_for_decision(self) -> None:
        model = (
            FakeChatModel()
            .with_response(tool_call("ask_user", {"question": "Early check-in?", "options": ["Yes", "No"]}))
            .with_response(AIMessage(content="Pick one."))
        )
        adapter, bot, _sessions = await _make_adapter(model)
        reply = await adapter.handle_inbound("chat:1", "help me")
        assert any(isinstance(a, RequestUserDecision) for a in reply.artifacts)
        assert bot.sent[-1][2] is not None  # markup present

    async def test_callback_resumes_agent_with_choice(self) -> None:
        # First turn asks; the callback feeds "Yes" back as the next user message.
        model = (
            FakeChatModel()
            .with_response(AIMessage(content="Got it — you want early check-in."))
        )
        adapter, bot, _sessions = await _make_adapter(model)
        await adapter.handle_callback("chat:1", "Yes", "cq-1")
        assert "cq-1" in bot.answered
        assert bot.sent[-1][1].startswith("Got it")


class TestOutbound:
    async def test_notify_routes_to_chat_id(self) -> None:
        bot = RecordingBot()
        sessions = InMemoryChannelSessionRepository()
        from domain.entities import ChannelSession

        await sessions.upsert(
            ChannelSession(client_token="tok", channel=Channel.TELEGRAM, address="chat:9")
        )
        notifier = TelegramClientNotifier(bot=bot, sessions=sessions)
        await notifier.notify(
            ProgressEvent(
                client_token="tok",
                booking_id="b1",
                kind="sent",
                subject="Message sent",
                body="We asked the hotel about early check-in.",
            )
        )
        assert bot.sent == [
            ("chat:9", "Message sent\n\nWe asked the hotel about early check-in.", None)
        ]

    async def test_notify_no_session_is_noop(self) -> None:
        bot = RecordingBot()
        notifier = TelegramClientNotifier(bot=bot, sessions=InMemoryChannelSessionRepository())
        await notifier.notify(
            ProgressEvent(
                client_token="tok", booking_id="b1", kind="sent", subject="s", body="b"
            )
        )
        assert bot.sent == []
