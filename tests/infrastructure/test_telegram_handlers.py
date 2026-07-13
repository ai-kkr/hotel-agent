"""aiogram router/handler tests (design D1/D2).

Feeds scripted ``Update`` objects into the aiogram ``Dispatcher`` (no real Telegram calls: a fake
adapter records calls instead of sending). This is the aiogram-native way to test routing — the
manual ``getUpdates`` poll loop is gone, so there is no "polling" test anymore.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Chat, Message, Update, User

from infrastructure.telegram.routers import build_router


class FakeAdapter:
    """Records handler calls without touching Telegram (no send → no real Bot API use)."""

    def __init__(self) -> None:
        self.starts: list[str] = []
        self.inbounds: list[tuple[str, str]] = []

    async def handle_start(self, chat_id: str) -> None:
        self.starts.append(chat_id)

    async def handle_inbound(self, chat_id: str, text: str) -> None:
        self.inbounds.append((chat_id, text))


def _make_dp() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(build_router())
    return dp


def _msg_update(text: str | None, *, chat_id: int = 4242, update_id: int = 1) -> Update:
    return Update(
        update_id=update_id,
        message=Message(
            message_id=1,
            date=datetime(2024, 1, 1, tzinfo=UTC),
            chat=Chat(id=chat_id, type="private"),
            from_user=User(id=chat_id, is_bot=False, first_name="x"),
            text=text,
        ),
    )


@pytest.fixture
async def bot() -> Bot:
    # A throwaway token; never used for real calls (the fake adapter doesn't send). Session closed
    # after the test to avoid aiohttp resource warnings.
    b = Bot(token="0:fake")
    yield b  # type: ignore[misc]
    await b.session.close()


class TestHandlers:
    async def test_start_routes_to_handle_start(self, bot: Bot) -> None:
        dp = _make_dp()
        adapter = FakeAdapter()
        await dp.feed_update(bot, _msg_update("/start"), surface_adapter=adapter)
        assert adapter.starts == ["4242"]
        assert adapter.inbounds == []

    async def test_start_with_deep_link_payload_also_routes(self, bot: Bot) -> None:
        dp = _make_dp()
        adapter = FakeAdapter()
        await dp.feed_update(bot, _msg_update("/start invite_xyz"), surface_adapter=adapter)
        assert adapter.starts == ["4242"]

    async def test_text_routes_to_handle_inbound(self, bot: Bot) -> None:
        dp = _make_dp()
        adapter = FakeAdapter()
        await dp.feed_update(bot, _msg_update("early check-in please"), surface_adapter=adapter)
        assert adapter.inbounds == [("4242", "early check-in please")]
        assert adapter.starts == []

    async def test_non_text_message_is_ignored(self, bot: Bot) -> None:
        dp = _make_dp()
        adapter = FakeAdapter()
        await dp.feed_update(bot, _msg_update(None), surface_adapter=adapter)
        assert adapter.inbounds == []
        assert adapter.starts == []
