"""Telegram "typing…" indicator helper for agent nodes.

Keeps the chat action alive while a node does real work (the LLM call, tool execution). Per-node
(not workflow-wide): the agent's own message sends clear the indicator, so a workflow-wide loop
would fight them. Takes a bare ``chat_id`` (``None`` when there's no Telegram chat) so it has no
dependency on :class:`EmailContext` / :class:`Runtime`.
"""

from contextlib import asynccontextmanager

from src.bot.utils import bot_typing


@asynccontextmanager
async def typing(chat_id: int | None):
    """Hold the typing indicator for the duration of the block, or no-op when ``chat_id`` is falsy."""
    if not chat_id:
        yield
        return
    from src.bot.app import get_bot

    async with bot_typing(get_bot(), chat_id):
        yield
