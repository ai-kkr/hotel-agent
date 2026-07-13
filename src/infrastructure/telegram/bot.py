"""aiogram-backed :class:`TelegramBotPort` (design D1).

A thin adapter from the surface module's :class:`TelegramBotPort` protocol onto ``aiogram.Bot``.
Kept minimal on purpose — it exists so the adapter/notifier stay unit-testable with a recording fake
while production sends through the real Bot. The raw ``aiogram.Bot`` is exposed via :attr:`raw` for
the polling entrypoint (:func:`infrastructure.telegram.run.start_telegram`).
"""

from __future__ import annotations

from typing import Any

from aiogram import Bot


class AiogramBotPort:
    """:class:`TelegramBotPort` implementation backed by ``aiogram.Bot``."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        *,
        parse_mode: str | None = None,
    ) -> None:
        # reply_markup is unused — the surface is free-text only (no keyboards). Kept on the signature
        # to match TelegramBotPort / the recording fake in tests.
        await self._bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)

    async def send_chat_action(self, chat_id: str, action: str) -> None:
        await self._bot.send_chat_action(chat_id=chat_id, action=action)

    @property
    def raw(self) -> Bot:
        """The underlying ``aiogram.Bot`` — used by the polling entrypoint."""
        return self._bot
