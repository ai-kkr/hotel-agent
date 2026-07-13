"""aiogram router for the Telegram surface (design D1/D2).

Module-level router factory: handlers are registered on a fresh :class:`Router` and resolve their
collaborator (the :class:`TelegramAdapter`) from aiogram's dependency-injection context (the
``surface_adapter`` kwarg), **not** from a closure. The DI value is provided at polling start by
:func:`infrastructure.telegram.run.start_telegram` (``dp.start_polling(bot, surface_adapter=...)``).

Handlers are intentionally thin: they translate aiogram ``Message`` into the adapter's surface-
agnostic ``chat_id`` + ``text`` and let the adapter own mailbox resolution, the agent turn, and
rendering.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from infrastructure.logging import get_logger
from infrastructure.telegram.adapter import TelegramAdapter

_log = get_logger(__name__)


def build_router() -> Router:
    """Build the Telegram surface router with ``/start`` and message handlers."""
    router = Router()

    @router.message(CommandStart())
    async def handle_start(message: Message, surface_adapter: TelegramAdapter) -> None:
        """``/start`` → resolve/create mailbox + send the greeting with the forward address."""
        chat_id = str(message.chat.id)
        await surface_adapter.handle_start(chat_id)
        _log.info("telegram.start", chat_id=chat_id)

    @router.message()
    async def handle_message(message: Message, surface_adapter: TelegramAdapter) -> None:
        """Inbound text → one surface-agent turn (adapter renders + sends the reply)."""
        if not message.text:
            return  # non-text updates are out of scope (allowed_updates == ["message"] w/ text)
        chat_id = str(message.chat.id)
        await surface_adapter.handle_inbound(chat_id, message.text)
        _log.info("telegram.message", chat_id=chat_id)

    return router
