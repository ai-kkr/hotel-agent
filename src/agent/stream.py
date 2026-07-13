import asyncio
import contextlib

from aiogram.enums import ChatAction
from aiogram.types import MessageEntity
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from telegramify_markdown import convert, split_entities

from src.config import get_settings
from src.context import get_context
from src.db.models import ClientORM
from src.logging import get_logger

from .context import EmailContext
from .types import MessageText

log = get_logger(__name__)

#: Telegram shows the "typing…" indicator for ~5 s; re-trigger it on this cadence while working.
_TYPING_INTERVAL = 4.0
#: Telegram caps a single message at 4096 UTF-16 code units.
_TG_MAX_LEN = 4096
#: Placeholder the agent puts in its text where the client's forwarding inbox should appear; it is
#: substituted with ``ClientORM.inbox`` when rendering (after streaming, so the token can't be split
#: across streamed chunks).
_INBOX_PLACEHOLDER = "$user_inbox"


async def stream_graph(
    msg: str,
    client: ClientORM,
) -> None:
    """Drive a single agent turn (or resume an ``interrupt``) and relay its output to the chat.

    - Sends a ``typing…`` chat action for as long as the agent is working.
    - Streams ``custom``-mode :class:`MessageText` (agent narrations) live.
    - Reassembles the agent's streamed ``AIMessage`` text (``messages`` mode yields
      ``(message, metadata)`` tuples, possibly in many chunks) and sends each distinct message as
      a single chat message.
    """
    ctx = get_context()
    bot = ctx.bot
    graph = ctx.email_graph  # type: ignore[assignment]
    config = RunnableConfig(configurable={"thread_id": client.thread_id})  # type: ignore[assignment]
    context = EmailContext(
        from_email=get_settings().mailtrap_from_email or None,
        reply_to=client.inbox,
        user_email=client.email,
        client_id=client.id,
    )

    chat_id = client.telegram_id
    if not chat_id:
        return

    # Substitute the agent's ``$user_inbox`` placeholder with the client's forwarding address.
    inbox = client.inbox or ""

    # If the graph is paused on an interrupt (e.g. ``ask_user`` waiting for the user's reply),
    # resume it with the incoming message; otherwise start a fresh agent turn.
    state = await graph.aget_state(config)
    interrupted = any(task.interrupts for task in state.tasks)
    inp = Command(resume=msg) if interrupted else {"messages": [HumanMessage(content=msg)]}

    async with _typing(bot, chat_id):
        # message_id -> accumulated text so far; each distinct AIMessage becomes one chat message.
        acc: dict[str, str] = {}
        current_id: str | None = None

        async for mode, payload in graph.astream(
            inp,
            config=config,
            context=context,  # ty:ignore[invalid-argument-type]
            stream_mode=["custom", "messages"],
        ):
            if mode == "custom" and isinstance(payload, MessageText):
                await _send_text(bot, chat_id, payload.text, inbox=inbox)
                continue

            if mode != "messages":
                continue
            # ``messages`` mode payload is a (message, metadata) tuple.
            message, _meta = payload  # type: ignore[misc]
            if not isinstance(message, AIMessage | AIMessageChunk):
                continue
            content = message.content
            if not isinstance(content, str) or not content:
                continue
            mid = getattr(message, "id", None) or "_"
            if current_id is not None and mid != current_id:
                await _flush(bot, chat_id, acc, current_id, inbox=inbox)
            current_id = mid
            acc[mid] = acc.get(mid, "") + content

        if current_id is not None:
            await _flush(bot, chat_id, acc, current_id, inbox=inbox)


async def _send_text(bot, chat_id: int, text: str, *, inbox: str = "") -> None:
    """Render ``text`` as Telegram formatting and send it.

    The agent emits ordinary Markdown. We convert it to ``(plain_text, entities)`` with
    :func:`telegramify_markdown.convert` and send via ``entities=`` (no ``parse_mode`` — the two
    are mutually exclusive, and entities avoid MarkdownV2's brittle escaping entirely). Long
    messages are split at the 4096 UTF-16 limit; anything unexpected falls back to plain text.

    ``$user_inbox`` placeholders in ``text`` are replaced with ``inbox`` (the client's forwarding
    address) before rendering.
    """
    if inbox:
        text = text.replace(_INBOX_PLACEHOLDER, inbox)
    try:
        plain, entities = convert(text)
    except Exception as e:  # conversion should not fail, but never drop a message over it
        log.debug("md.convert_failed", error=str(e))
        plain, entities = text, []

    try:
        for chunk_text, chunk_entities in split_entities(plain, entities, _TG_MAX_LEN):
            await bot.send_message(
                chat_id=chat_id,
                text=chunk_text,
                entities=[MessageEntity(**e.to_dict()) for e in chunk_entities] or None,
            )
    except Exception as e:  # last-resort delivery as plain text
        log.warning("send.formatted_failed", error=str(e))
        await bot.send_message(chat_id=chat_id, text=text)


@contextlib.asynccontextmanager
async def _typing(bot, chat_id: int):
    """Keep the chat's "typing…" indicator alive for the duration of the ``async with`` block."""
    stop = asyncio.Event()
    task = asyncio.create_task(_keep_typing(bot, chat_id, stop))
    try:
        yield
    finally:
        stop.set()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def _keep_typing(bot, chat_id: int, stop: asyncio.Event) -> None:
    """Keep the chat's "typing…" indicator alive until ``stop`` is set."""
    while not stop.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as e:  # typing is best-effort, must not break the stream
            log.debug("typing.send_failed", error=str(e))
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=_TYPING_INTERVAL)


async def _flush(bot, chat_id: int, acc: dict[str, str], mid: str, *, inbox: str = "") -> None:
    """Send the accumulated text for ``mid`` as a single chat message and clear it."""
    text = acc.pop(mid, "")
    if text:
        await _send_text(bot, chat_id, text, inbox=inbox)
