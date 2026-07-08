"""Telegram adapter (spec: telegram-surface; design D4, D7).

The concrete channel adapter for the surface-agnostic agent. Responsibilities (spec
telegram-surface):

(a) receive chat messages and forward them to the surface agent thread keyed by the client's
    ``ChannelSession`` (chat_id);
(b) render agent artifacts — ``RequestUserDecision`` → inline keyboard, text → chat message;
(c) implement the outbound progress port for the Telegram channel (a ``ClientNotifier``).

The adapter talks to Telegram through :class:`TelegramBotPort` (an httpx client in production, a
recording fake in tests) — no real Telegram calls happen in the test suite. Button presses are
normalized into a follow-up that resumes the agent (the choice is fed back as the client's answer).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from domain.application import MailboxService
from domain.enums import Channel
from domain.intents import RequestUserDecision
from domain.ports import ProgressEvent
from infrastructure.agents.surface import SurfaceAgent, SurfaceReply


class TelegramBotPort(Protocol):
    """The Telegram Bot API surface the adapter depends on (faked in tests)."""

    async def send_message(
        self, chat_id: str, text: str, reply_markup: dict[str, Any] | None = None
    ) -> None: ...

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> None: ...

    async def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]: ...


class HttpTelegramBot:
    """Thin Telegram Bot API client over httpx (no extra dependency)."""

    def __init__(self, bot_token: str, client: httpx.AsyncClient | None = None) -> None:
        self._base = f"https://api.telegram.org/bot{bot_token}"
        self._client = client

    async def _call(
        self, method: str, payload: dict[str, Any], *, timeout: float | None = None
    ) -> dict[str, Any]:
        """POST a Bot API method; return the parsed JSON body (raises on non-2xx)."""
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            resp = await client.post(
                f"{self._base}/{method}", json=payload, timeout=timeout or 30.0
            )
            resp.raise_for_status()
            return resp.json()
        finally:
            if owns:
                await client.aclose()

    async def send_message(
        self, chat_id: str, text: str, reply_markup: dict[str, Any] | None = None
    ) -> None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        await self._call("sendMessage", payload)

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        await self._call(
            "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text}
        )

    async def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        """Long-poll ``getUpdates``. ``timeout`` is the server long-poll seconds; the HTTP client
        read timeout is padded so the request outlives the poll."""
        # Only request the update kinds we handle (keeps the response small).
        data = await self._call(
            "getUpdates",
            {
                "offset": offset,
                "timeout": timeout,
                "allowed_updates": ["message", "callback_query"],
            },
            timeout=timeout + 15,
        )
        return list(data.get("result") or [])


# --- rendering (adapter-owned; the agent never imports Telegram types) ------------------------


def render_inline_keyboard(decision: RequestUserDecision) -> dict[str, Any]:
    """Render a ``RequestUserDecision`` as a Telegram inline keyboard.

    ``callback_data`` carries the chosen option back on a button press (kept short; the option text
    is the value). Options are URL-encoded-safe by Telegram's 64-byte limit on callback_data.
    """
    buttons = [{"text": opt, "callback_data": _encode_option(opt)} for opt in decision.options]
    return {"inline_keyboard": [buttons]}


def render_reply(reply: SurfaceReply) -> tuple[str, dict[str, Any] | None]:
    """Render a surface reply into (text, optional reply_markup).

    If the reply carries a ``RequestUserDecision``, the markup is its inline keyboard and the text
    is the decision's question (any agent text is prepended). Other artifacts (e.g. CancelBooking)
    are not rendered here — they are executed by a service, not shown as UI.
    """
    text = reply.text
    markup: dict[str, Any] | None = None
    for artifact in reply.artifacts:
        if isinstance(artifact, RequestUserDecision):
            markup = render_inline_keyboard(artifact)
            question = artifact.question
            text = f"{text}\n\n{question}".strip() if text else question
    return text, markup


def normalize_callback(data: str) -> str:
    """Decode a button-press ``callback_data`` back into the chosen option text."""
    return _decode_option(data)


def _encode_option(option: str) -> str:
    # callback_data is opaque to Telegram; store the verbatim option (truncated for the 64-byte cap).
    return option[:64]


def _decode_option(data: str) -> str:
    return data


@dataclass
class TelegramAdapter:
    """Bind the surface agent to Telegram: inbound routing, rendering, outbound progress."""

    bot: TelegramBotPort
    agent: SurfaceAgent
    sessions: Any  # ChannelSessionRepository (typed loosely to avoid an import cycle)
    mailbox: MailboxService
    channel: Channel = Channel.TELEGRAM

    async def handle_inbound(self, chat_id: str, text: str) -> SurfaceReply:
        """One inbound chat message → a surface-agent turn → rendered + sent to the chat."""
        # Ensure the client/mailbox exists (lazy); the agent thread is keyed by chat_id.
        await self.mailbox.resolve_or_create(self.channel, chat_id)
        reply = await self.agent.converse(chat_id, text)
        out_text, markup = render_reply(reply)
        if out_text:
            await self.bot.send_message(chat_id, out_text, reply_markup=markup)
        return reply

    async def handle_callback(
        self, chat_id: str, callback_data: str, callback_query_id: str
    ) -> SurfaceReply:
        """A button press: normalize the choice and resume the agent with it as the answer."""
        await self.bot.answer_callback_query(callback_query_id)
        choice = normalize_callback(callback_data)
        reply = await self.agent.converse(chat_id, choice)
        out_text, _markup = render_reply(reply)
        if out_text:
            await self.bot.send_message(chat_id, out_text)
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
