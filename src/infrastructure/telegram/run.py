"""aiogram polling entrypoint (design D1/D10).

Starts the aiogram ``Dispatcher`` long-poller as a background :class:`asyncio.Task`. Only one process
may poll a given bot token at a time (Telegram rejects concurrent ``getUpdates``), so this is the
single inbound path. DI kwargs (e.g. ``surface_adapter``) are forwarded to
``Dispatcher.start_polling`` and reach handlers via aiogram's context.

``handle_signals=False`` is mandatory here: polling runs inside the uvicorn event loop, which already
owns SIGINT/SIGTERM. aiogram's default ``handle_signals=True`` would register its own signal handlers
on the same loop and trip its ``_stop_signal``, stopping polling immediately (you'd see just
``Start polling`` → ``Polling stopped``).

The caller owns the returned task: cancel it on shutdown, then close ``bot.session``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from aiogram import Bot, Dispatcher

from infrastructure.logging import get_logger

_log = get_logger(__name__)


def start_telegram(bot: Bot, dp: Dispatcher, **di: Any) -> asyncio.Task[None]:
    """Run ``dp.start_polling(bot, **di)`` as a named background task.

    Args:
        bot: The aiogram ``Bot`` to poll for.
        dp: The configured ``Dispatcher`` (with routers included).
        **di: Dependency-injection kwargs forwarded into handler context
            (e.g. ``surface_adapter=<TelegramAdapter>``).

    Returns:
        The polling task; cancel it on shutdown.
    """
    task = asyncio.create_task(
        dp.start_polling(bot, handle_signals=False, **di), name="telegram-poll"
    )
    # Surface polling failures instead of silently losing them as "Task exception was never retrieved".
    task.add_done_callback(_log_polling_failure)
    return task


def _log_polling_failure(task: asyncio.Task[None]) -> None:
    if task.cancelled():
        _log.info("telegram.polling.cancelled")
        return
    exc = task.exception()
    if exc is not None:
        _log.exception("telegram.polling.failed", error=str(exc))

