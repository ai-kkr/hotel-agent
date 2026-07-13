"""Telegram channel package.

Surface-agnostic :class:`TelegramAdapter` + outbound notifier, an aiogram-backed
:class:`TelegramBotPort`, the aiogram router, and the polling entrypoint.
"""

from infrastructure.telegram.adapter import (
    TelegramAdapter,
    TelegramBotPort,
    TelegramClientNotifier,
)
from infrastructure.telegram.bot import AiogramBotPort
from infrastructure.telegram.routers import build_router
from infrastructure.telegram.run import start_telegram

__all__ = [
    "AiogramBotPort",
    "TelegramAdapter",
    "TelegramBotPort",
    "TelegramClientNotifier",
    "build_router",
    "start_telegram",
]
