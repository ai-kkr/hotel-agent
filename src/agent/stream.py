import asyncio
import contextlib
import re

from aiogram.enums import ChatAction, ParseMode
from aiogram.utils.text_decorations import html_decoration
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.config import get_settings
from src.context import get_context
from src.db.models import ClientORM
from src.logging import get_logger

from .context import EmailContext
from .tracing import with_tracing
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
#: Trailing punctuation the agent tends to put right after ``$user_inbox`` mid-sentence
#: (``. , ; : ! ?``) — consumed on substitution so it doesn't dangle as a stray char after the
#: ``<pre>`` block.
_INBOX_TRAILING_PUNCT_RE = re.compile(
    re.escape(_INBOX_PLACEHOLDER) + r"\s*([.,;:!?])"
)


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
    graph = ctx.email_graph_or_raise()
    config = RunnableConfig(configurable={"thread_id": client.thread_id})  # type: ignore[assignment]
    # Attach Langfuse tracing (user_id = client, session_id = thread) — unchanged when disabled.
    config = with_tracing(config, client)
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
        # message_id -> True when that AIMessage carries a tool call (i.e. it's the agent's
        # internal "thought"/draft before acting, not a final answer). Such content is never meant
        # for the guest — narration goes through ``inform_step`` / tool progress — so we suppress
        # it to stop e.g. a drafted hotel letter or a free-form summary from leaking into chat.
        is_action: dict[str, bool] = {}
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
            mid = getattr(message, "id", None) or "_"
            if _has_tool_calls(message):
                is_action[mid] = True
            content = message.content
            if not isinstance(content, str) or not content:
                continue
            if current_id is not None and mid != current_id:
                await _flush(
                    bot,
                    chat_id,
                    acc,
                    current_id,
                    inbox=inbox,
                    suppress=is_action.get(current_id, False),
                )
            current_id = mid
            acc[mid] = acc.get(mid, "") + content

        if current_id is not None:
            await _flush(
                bot,
                chat_id,
                acc,
                current_id,
                inbox=inbox,
                suppress=is_action.get(current_id, False),
            )


def _has_tool_calls(message: AIMessage | AIMessageChunk) -> bool:
    """True if this AIMessage carries tool calls (a tool-call chunk on streaming or full on done).

    Such messages are the agent's internal action/draft step, not a guest-facing answer.
    """
    if getattr(message, "tool_calls", None):
        return True
    return bool(getattr(message, "tool_call_chunks", None))


async def send_formatted(bot, chat_id: int, text: str) -> None:
    """Render a Markdown ``text`` as Telegram formatting and send it (no ``$user_inbox`` sub).

    Public entry point for one-off chat messages outside the agent stream (e.g. webhook
    notifications). For agent output use :func:`_send_text`, which also substitutes the inbox
    placeholder.
    """
    await _send_text(bot, chat_id, text)


async def _send_text(bot, chat_id: int, text: str, *, inbox: str = "") -> None:
    """Send ``text`` to the chat as Telegram HTML.

    The agent emits Telegram HTML directly (``<b>``, ``<i>``, ``<code>``, ``<a>``). The literal
    ``$user_inbox`` placeholder is replaced with the real inbox address wrapped in a ``<pre>``
    block and HTML-escaped, so the guest sees it as a wide monospace block and can copy it with one
    tap. Long messages
    are split at Telegram's 4096 UTF-16 limit, on newline boundaries. Anything unexpected falls
    back to delivering the text tag-stripped.
    """
    if inbox:
        # Drop trailing punctuation the agent placed right after ``$user_inbox`` mid-sentence so
        # it doesn't dangle after the ``<pre>`` block, then wrap the address itself.
        text = _INBOX_TRAILING_PUNCT_RE.sub(_INBOX_PLACEHOLDER, text)
        text = text.replace(_INBOX_PLACEHOLDER, f"<pre>{html_decoration.quote(inbox)}</pre>")
    try:
        for chunk in _split_html(text, _TG_MAX_LEN):
            await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=ParseMode.HTML)
    except Exception as e:  # last-resort delivery as plain text
        log.warning("send.formatted_failed", error=str(e))
        await bot.send_message(chat_id=chat_id, text=_TAG_RE.sub("", text))


def _split_html(text: str, max_len: int) -> list[str]:
    """Split ``text`` into chunks of at most ``max_len`` UTF-16 code units, on newline boundaries.

    A single line longer than the budget is hard-split by codepoint (rare for chat messages; may
    sever an HTML tag, accepted as an edge case). Whitespace-only chunks are dropped — Telegram
    rejects them as empty text.
    """
    if _utf16_len(text) <= max_len:
        return [text] if text.strip() else []

    chunks: list[str] = []
    buf = ""
    for line in text.split("\n"):
        candidate = line if not buf else buf + "\n" + line
        if _utf16_len(candidate) <= max_len:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
            buf = ""
        if _utf16_len(line) > max_len:
            chunks.extend(_hard_split(line, max_len))
        else:
            buf = line
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c.strip()]


def _hard_split(line: str, max_len: int) -> list[str]:
    """Split a single over-long line by codepoint into pieces of at most ``max_len`` UTF-16 units."""
    parts: list[str] = []
    buf = ""
    for ch in line:
        if buf and _utf16_len(buf + ch) > max_len:
            parts.append(buf)
            buf = ch
        else:
            buf += ch
    if buf:
        parts.append(buf)
    return parts


def _utf16_len(s: str) -> int:
    """Length of ``s`` in UTF-16 code units (the unit Telegram counts toward its 4096 limit)."""
    return len(s.encode("utf-16-le")) // 2


_TAG_RE = re.compile(r"<[^>]+>")


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


async def _flush(
    bot,
    chat_id: int,
    acc: dict[str, str],
    mid: str,
    *,
    inbox: str = "",
    suppress: bool = False,
) -> None:
    """Send the accumulated text for ``mid`` as a single chat message and clear it.

    ``suppress`` drops the message entirely — used for tool-carrying AIMessages (agent drafts that
    must not reach the guest, e.g. a composed hotel letter written as a "thought").
    """
    text = acc.pop(mid, "")
    if suppress or not text:
        return
    await _send_text(bot, chat_id, text, inbox=inbox)
