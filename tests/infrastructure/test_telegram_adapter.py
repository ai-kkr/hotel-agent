from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from tests.agents.fakes import FakeChatModel

from domain.application import ChatIntakeService, MailboxService
from domain.enums import Channel
from domain.ports import ProgressEvent
from infrastructure.agents.surface import SurfaceAgent, SurfaceDeps
from infrastructure.agents.tools import FakeWebFetcher, FakeWebSearcher
from infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryChannelSessionRepository,
    InMemoryClientRepository,
)
from infrastructure.telegram.adapter import (
    TelegramAdapter,
    TelegramClientNotifier,
    _typing,
    render_reply,
)


@dataclass
class RecordingBot:
    """A :class:`TelegramBotPort` fake that records outbound sends + chat actions."""

    sent: list[tuple[str, str, dict[str, Any] | None]] = field(default_factory=list)
    chat_actions: list[tuple[str, str]] = field(default_factory=list)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        *,
        parse_mode: str | None = None,
    ) -> None:
        self.sent.append((chat_id, text, reply_markup))

    async def send_chat_action(self, chat_id: str, action: str) -> None:
        self.chat_actions.append((chat_id, action))


class _NullGateway:
    async def start_booking(self, event: object) -> None: ...
    async def signal_hotel_reply(self, event: object) -> None: ...
    async def signal_client_message(self, event: object) -> None: ...
    async def signal_delivery_failure(self, *args: object) -> None: ...


async def _make_adapter(
    model: FakeChatModel, *, typing_interval: float = 4.0
) -> tuple[TelegramAdapter, RecordingBot, MailboxService]:
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
    adapter = TelegramAdapter(
        bot=bot, agent=agent, sessions=sessions, mailbox=mailbox, typing_interval=typing_interval
    )
    return adapter, bot, mailbox


class TestRendering:
    def test_render_reply_is_text_only_with_no_markup(self) -> None:
        # Free-text surface: a reply renders to its text with no markup (no keyboards).
        from infrastructure.agents.surface import SurfaceReply

        text, markup = render_reply(SurfaceReply(text="hi"))
        assert text == "hi"
        assert markup is None


class TestRouting:
    async def test_inbound_sends_text_with_no_markup(self) -> None:
        model = FakeChatModel().with_response(AIMessage(content="Hello there."))
        adapter, bot, _mailbox = await _make_adapter(model, typing_interval=3600)
        await adapter.handle_inbound("chat:1", "hi")
        assert len(bot.sent) == 1
        assert bot.sent[0][0] == "chat:1"
        assert bot.sent[0][1] == "Hello there."
        assert bot.sent[0][2] is None  # free-text: never any markup

    async def test_inbound_never_attaches_keyboard(self) -> None:
        # ask_user now returns free-text hints, so even a questioning reply has no markup.
        from tests.agents.fakes import tool_call

        model = FakeChatModel().with_response(
            tool_call("ask_user", {"question": "Early check-in?", "options": ["Yes", "No"]})
        ).with_response(AIMessage(content="Let me know your wishes."))
        adapter, bot, _mailbox = await _make_adapter(model, typing_interval=3600)
        await adapter.handle_inbound("chat:1", "help me")
        assert bot.sent, "expected at least one outbound message"
        assert all(entry[2] is None for entry in bot.sent)  # no markup ever attached


class TestStartCommand:
    async def test_start_creates_mailbox_and_reveals_forward_address(self) -> None:
        model = FakeChatModel()
        adapter, bot, _mailbox = await _make_adapter(model)
        await adapter.handle_start("chat:42")
        assert len(bot.sent) == 1
        chat_id, text, _markup = bot.sent[0]
        assert chat_id == "chat:42"
        # The greeting states the client's individual c.<token>@ forward address.
        assert "c.tok@kkr-hotel.com" in text

    async def test_start_is_idempotent_same_address(self) -> None:
        model = FakeChatModel()
        adapter, bot, _mailbox = await _make_adapter(model)
        await adapter.handle_start("chat:42")
        await adapter.handle_start("chat:42")
        # Repeat /start: same address, no second mailbox created.
        assert len(bot.sent) == 2
        assert "c.tok@kkr-hotel.com" in bot.sent[0][1]
        assert "c.tok@kkr-hotel.com" in bot.sent[1][1]


class TestTypingIndicator:
    async def test_typing_fires_during_block_and_stops_after(self) -> None:
        # The ticker resends "typing" while the block runs; after exit it stops.
        bot = RecordingBot()
        async with _typing(bot, "chat:7", interval=0.01):
            await asyncio.sleep(0.03)  # long enough for at least one tick
        fired_during = [a for a in bot.chat_actions if a == ("chat:7", "typing")]
        assert fired_during, "typing action should fire at least once during the block"
        count_after_block = len(bot.chat_actions)
        await asyncio.sleep(0.03)  # no further ticks after exit
        assert len(bot.chat_actions) == count_after_block


class TestOutbound:
    async def test_notify_routes_to_chat_id(self) -> None:
        from domain.entities import ChannelSession

        bot = RecordingBot()
        sessions = InMemoryChannelSessionRepository()
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
        assert bot.sent == [("chat:9", "Message sent\n\nWe asked the hotel about early check-in.", None)]

    async def test_notify_no_session_is_noop(self) -> None:
        bot = RecordingBot()
        notifier = TelegramClientNotifier(bot=bot, sessions=InMemoryChannelSessionRepository())
        await notifier.notify(
            ProgressEvent(client_token="tok", booking_id="b1", kind="sent", subject="s", body="b")
        )
        assert bot.sent == []
