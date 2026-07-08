"""Telegram long-polling loop (design D10; the bot process inbound path).

Drives :class:`infrastructure.telegram.adapter.TelegramAdapter` by long-polling Telegram
``getUpdates``. Each update is dispatched: a text message → ``handle_inbound``; an inline-keyboard
button press → ``handle_callback``. The ``update_id`` offset advances so acknowledged updates are
not re-delivered.

This is the inbound half of the Telegram surface. The outbound half (worker → chat via
:class:`TelegramClientNotifier`) runs in the worker process and needs no poller.

Resilient: a failed poll (network/Telegram 5xx) is logged and retried after a back-off; one bad
update does not kill the loop. Cancellation (process shutdown) exits cleanly.
"""

from __future__ import annotations

import asyncio
from typing import Any

from infrastructure.logging import get_logger
from infrastructure.telegram.adapter import TelegramAdapter

_log = get_logger(__name__)

# Back-off between failed polls (seconds). Keeps a down Telegram API from spinning the CPU.
ERROR_BACKOFF_SECONDS = 5


async def run_telegram(adapter: TelegramAdapter, *, poll_timeout: int = 30) -> None:
    """Poll Telegram forever, dispatching updates to the adapter.

    Runs until cancelled (the caller cancels the task on shutdown). ``poll_timeout`` is the
    server-side long-poll duration (matches ``KKR_TELEGRAM_POLL_TIMEOUT_SECONDS``).
    """
    offset: int | None = None
    _log.info("telegram.polling.started", poll_timeout=poll_timeout)
    while True:
        try:
            updates = await adapter.bot.get_updates(offset=offset, timeout=poll_timeout)
        except asyncio.CancelledError:
            _log.info("telegram.polling.stopped")
            raise
        except Exception:
            _log.exception("telegram.polling.error")
            await asyncio.sleep(ERROR_BACKOFF_SECONDS)
            continue

        for update in updates:
            # Advance the offset past this update so Telegram won't redeliver it.
            uid = update.get("update_id")
            if isinstance(uid, int):
                offset = uid + 1
            try:
                await dispatch_update(adapter, update)
            except Exception:
                # One malformed/unroutable update must not stop the loop.
                _log.exception("telegram.dispatch.error", update_id=uid)


async def dispatch_update(adapter: TelegramAdapter, update: dict[str, Any]) -> None:
    """Route one Telegram update to the adapter (message → inbound, callback → callback)."""
    if _is_text_message(update):
        msg = update["message"]
        chat_id = str(msg["chat"]["id"])
        await adapter.handle_inbound(chat_id, msg["text"])
    elif update.get("callback_query"):
        cq = update["callback_query"]
        chat = cq.get("message", {}).get("chat", {})
        chat_id = str(chat.get("id"))
        data = cq.get("data") or ""
        callback_id = cq.get("id") or ""
        if chat_id:
            await adapter.handle_callback(chat_id, data, callback_id)


def _is_text_message(update: dict[str, Any]) -> bool:
    msg = update.get("message")
    return bool(msg) and bool(msg.get("text")) and bool(msg.get("chat", {}).get("id"))
