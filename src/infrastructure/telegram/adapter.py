"""Telegram adapter (spec: telegram-surface; design D4, D6, D7).

The concrete channel adapter for the surface-agnostic agent. Responsibilities (spec
telegram-surface):

(a) receive chat messages and forward them to the surface agent thread keyed by the client's
    ``ChannelSession`` (chat_id);
(b) render agent text replies as chat messages (the agent emits no channel-specific UI artifacts);
(c) implement the outbound progress port for the Telegram channel (a ``ClientNotifier``).

Inbound polling is driven by aiogram (``aiogram.Dispatcher`` + ``Router`` — see :mod:`infrastructure.telegram.routers``);
the adapter talks to Telegram for **outbound** sends (replies, greeting, progress) through
:class:`TelegramBotPort` — an ``aiogram.Bot`` wrapper in production (see :mod:`infrastructure.telegram.bot``),
a recording fake in tests. No real Telegram calls happen in the test suite.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any, Protocol

from domain.application import MailboxService
from domain.enums import Channel
from domain.ports import ProgressEvent
from infrastructure.agents.surface import SurfaceAgent, SurfaceReply


class TelegramBotPort(Protocol):
    """The Telegram Bot API surface the adapter sends through (faked in tests)."""

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        *,
        parse_mode: str | None = None,
    ) -> None: ...

    async def send_chat_action(self, chat_id: str, action: str) -> None: ...


# --- rendering (adapter-owned; the agent never imports Telegram types) ------------------------


def render_reply(reply: SurfaceReply) -> tuple[str, dict[str, Any] | None]:
    """Render a surface reply into (text, optional reply_markup).

    The reply text is rendered as a chat message. Artifacts (e.g. ``CancelBooking``) are not rendered
    here — they are executed by a service, not shown as UI. ``reply_markup`` is always ``None`` now
    that the surface is free-text only (no inline keyboards).
    """
    return reply.text, None


@asynccontextmanager
async def _typing(bot: TelegramBotPort, chat_id: str, *, interval: float = 4.0) -> AsyncIterator[None]:
    """Emit the "typing" chat action every ``interval`` seconds for the duration of the block.

    Telegram's typing indicator expires after ~5s, so we resend periodically to keep the chat
    informed while a (potentially long) agent turn runs. Cancelled on block exit.
    """

    async def tick() -> None:
        while True:
            try:
                await bot.send_chat_action(chat_id, "typing")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    task = asyncio.create_task(tick())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@dataclass
class TelegramAdapter:
    """Bind the surface agent to Telegram: inbound routing, rendering, outbound progress."""

    bot: TelegramBotPort
    agent: SurfaceAgent
    sessions: Any  # ChannelSessionRepository (typed loosely to avoid an import cycle)
    mailbox: MailboxService
    channel: Channel = Channel.TELEGRAM
    typing_interval: float = 4.0  # seconds between "typing" resends during an agent turn

    async def handle_start(self, chat_id: str) -> None:
        """Handle ``/start``: resolve/create the mailbox and send a greeting stating capabilities
        and the client's individual ``c.<token>@`` forward address (spec: start command greeting)."""
        mailbox_address = await self.mailbox.resolve_or_create(self.channel, chat_id)
        # HTML formatting (parse_mode="HTML") — Telegram parses <b>/<code>; the address is monospaced.
        greeting = (
            "<b>🏨 Hotel concierge assistant</b>\n\n"
            "I can help you:\n"
            "• Answer questions about your hotel (menu, services, prices)\n"
            "• Collect your booking confirmation and negotiate with the hotel on your behalf\n"
            "• Track your active requests and report back\n\n"
            "Your personal forward address:\n"
            f"<code>{mailbox_address}</code>\n\n"
            "Forward a booking confirmation here (or to the address above), or just tell me your wishes!"
        )
        await self.bot.send_message(chat_id, greeting, parse_mode="HTML")

    async def handle_inbound(self, chat_id: str, text: str) -> SurfaceReply:
        """One inbound chat message → a surface-agent turn → rendered + sent to the chat.

        Emits the "typing" indicator for the duration of the agent turn (spec: typing indicator).
        """
        # Ensure the client/mailbox exists (lazy); the agent thread is keyed by chat_id.
        await self.mailbox.resolve_or_create(self.channel, chat_id)
        async with _typing(self.bot, chat_id, interval=self.typing_interval):
            reply = await self.agent.converse(chat_id, text)
        out_text, markup = render_reply(reply)
        if out_text:
            await self.bot.send_message(chat_id, out_text, reply_markup=markup)
        return reply


class TelegramClientNotifier:
    """The Telegram-channel :class:`ClientNotifier`: push a progress event to the client's chat.

    Resolves the client's ``chat_id`` via :class:`ChannelSessionRepository` (design D7 / spec
    client-communication). Idempotent delivery is the bot's concern (best-effort here).
    """

    def __init__(self, bot: TelegramBotPort, sessions: Any) -> None:
        self._bot = bot
        self._sessions = sessions

    async def notify(self, event: ProgressEvent) -> None:
        chat_id = await self._sessions.address_for(event.client_token, Channel.TELEGRAM)
        if chat_id is None:
            return  # client has no Telegram session → another channel's notifier handles it
        text = f"{event.subject}\n\n{event.body}" if event.subject else event.body
        await self._bot.send_message(chat_id, text)
