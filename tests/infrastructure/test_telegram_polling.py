from __future__ import annotations

import asyncio
from typing import Any

import pytest

from infrastructure.telegram import polling
from infrastructure.telegram.adapter import TelegramAdapter
from infrastructure.telegram.polling import dispatch_update, run_telegram


class FakeBot:
    """Yields scripted get_updates batches, then cancels to stop the loop."""

    def __init__(self, batches: list[list[dict[str, Any]]]) -> None:
        self._batches = iter(batches)
        self.offsets: list[int | None] = []
        self.sent: list[tuple[str, str]] = []
        self.answered: list[str] = []

    async def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        self.offsets.append(offset)
        try:
            return next(self._batches)
        except StopIteration:
            raise asyncio.CancelledError from None

    async def send_message(self, chat_id: str, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        self.sent.append((chat_id, text))

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        self.answered.append(callback_query_id)


class FakeAdapter:
    def __init__(self, bot: FakeBot) -> None:
        self.bot = bot
        self.inbound: list[tuple[str, str]] = []
        self.callbacks: list[tuple[str, str, str]] = []

    async def handle_inbound(self, chat_id: str, text: str) -> None:
        self.inbound.append((chat_id, text))

    async def handle_callback(self, chat_id: str, callback_data: str, callback_query_id: str) -> None:
        self.callbacks.append((chat_id, callback_data, callback_query_id))


def _msg(update_id: int, chat_id: int, text: str) -> dict[str, Any]:
    return {"update_id": update_id, "message": {"chat": {"id": chat_id}, "text": text}}


def _cb(update_id: int, chat_id: int, data: str, cq_id: str = "cq1") -> dict[str, Any]:
    return {
        "update_id": update_id,
        "callback_query": {"id": cq_id, "data": data, "message": {"chat": {"id": chat_id}}},
    }


class TestDispatch:
    async def test_text_message_routes_to_handle_inbound(self) -> None:
        bot = FakeBot([])
        adapter = FakeAdapter(bot)
        await dispatch_update(adapter, _msg(1, 4242, "hi"))  # type: ignore[arg-type]
        assert adapter.inbound == [("4242", "hi")]
        assert adapter.callbacks == []

    async def test_callback_query_routes_to_handle_callback(self) -> None:
        bot = FakeBot([])
        adapter = FakeAdapter(bot)
        await dispatch_update(adapter, _cb(2, 4242, "Yes"))  # type: ignore[arg-type]
        assert adapter.callbacks == [("4242", "Yes", "cq1")]
        assert adapter.inbound == []

    async def test_non_text_message_ignored(self) -> None:
        bot = FakeBot([])
        adapter = FakeAdapter(bot)
        # a message with no text (e.g. a sticker) is ignored gracefully
        await dispatch_update(adapter, {"update_id": 3, "message": {"chat": {"id": 1}}})  # type: ignore[arg-type]
        assert adapter.inbound == []


class TestRunTelegram:
    async def test_dispatches_updates_and_advances_offset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(polling, "ERROR_BACKOFF_SECONDS", 0)
        bot = FakeBot(
            [
                [_msg(10, 1, "hello"), _cb(11, 2, "Yes")],
                [_msg(12, 3, "again")],
            ]
        )
        adapter = FakeAdapter(bot)
        # The loop ends when get_updates raises CancelledError (batches exhausted).
        with pytest.raises(asyncio.CancelledError):
            await run_telegram(adapter, poll_timeout=1)  # type: ignore[arg-type]

        assert adapter.inbound == [("1", "hello"), ("3", "again")]
        assert adapter.callbacks == [("2", "Yes", "cq1")]
        # offset starts at None, then advances past the highest update_id seen so far;
        # the final get_updates (offset 13) returns no batches → CancelledError stops the loop.
        assert bot.offsets == [None, 12, 13]

    async def test_poll_error_is_retried_then_loop_continues(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(polling, "ERROR_BACKOFF_SECONDS", 0)

        class FlakyBot(FakeBot):
            def __init__(self) -> None:
                super().__init__([[_msg(20, 9, "after-recover")]])
                self._calls = 0

            async def get_updates(self, offset, timeout):  # type: ignore[no-untyped-def]
                self._calls += 1
                if self._calls == 1:
                    raise RuntimeError("telegram down")
                return await super().get_updates(offset, timeout)

        bot = FlakyBot()
        adapter = FakeAdapter(bot)
        with pytest.raises(asyncio.CancelledError):
            await run_telegram(adapter, poll_timeout=1)  # type: ignore[arg-type]
        # The error did not kill the loop: the recovered update was dispatched.
        assert adapter.inbound == [("9", "after-recover")]

    async def test_bad_update_does_not_stop_loop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(polling, "ERROR_BACKOFF_SECONDS", 0)
        bot = FakeBot(
            [
                [{"update_id": 30, "message": {"chat": {}}}, _msg(31, 7, "ok")],  # malformed then ok
            ]
        )
        adapter = FakeAdapter(bot)
        with pytest.raises(asyncio.CancelledError):
            await run_telegram(adapter, poll_timeout=1)  # type: ignore[arg-type]
        # The good update after the malformed one still went through.
        assert adapter.inbound == [("7", "ok")]


class TestTelegramAdapterIsPollable:
    def test_runtime_adapter_exposes_bot_for_polling(self) -> None:
        # The polling loop reads adapter.bot.get_updates; ensure the adapter exposes it.
        bot = FakeBot([])
        adapter = TelegramAdapter.__new__(TelegramAdapter)  # bypass __init__ (no agent needed)
        object.__setattr__(adapter, "bot", bot)
        assert hasattr(adapter.bot, "get_updates")
