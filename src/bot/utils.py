import asyncio
import contextlib
import re

from aiogram.enums import ChatAction, ParseMode
from aiogram.utils.text_decorations import html_decoration
from structlog import get_logger

#: Telegram shows the "typing…" indicator for ~5 s; re-trigger it on this cadence while working.
_TYPING_INTERVAL = 4.0
#: Telegram caps a single message at 4096 UTF-16 code units.
_TG_MAX_LEN = 4096
#: Placeholder the agent puts in its text where the client's forwarding inbox should appear; it is
#: substituted with the real inbox address when rendering to chat.
_INBOX_PLACEHOLDER = "$user_inbox"
#: Trailing punctuation the agent tends to put right after ``$user_inbox`` mid-sentence
#: (``. , ; : ! ?``) — consumed on substitution so it doesn't dangle as a stray char after the
#: ``<pre>`` block.
_INBOX_TRAILING_PUNCT_RE = re.compile(re.escape(_INBOX_PLACEHOLDER) + r"\s*([.,;:!?])")
#: Used to strip HTML tags for the plain-text fallback delivery.
_TAG_RE = re.compile(r"<[^>]+>")

log = get_logger(__name__)


@contextlib.asynccontextmanager
async def bot_typing(bot, chat_id: int):
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


async def send_formatted(bot, chat_id: int, text: str, *, inbox: str = "") -> None:
    """Render ``text`` as Telegram HTML and send it.

    The agent emits Telegram HTML directly (``<b>``, ``<i>``, ``<code>``, ``<a>``). Pass the client's
    inbox as ``inbox`` to substitute the ``$user_inbox`` placeholder with the real address wrapped in
    a ``<pre>`` block (copyable monospace); leave it empty for plain notifications with no
    placeholder. Long messages are split at Telegram's 4096 UTF-16 limit, on newline boundaries.
    Anything unexpected falls back to delivering the text tag-stripped.
    """
    if inbox:
        # Drop trailing punctuation the agent placed right after ``$user_inbox`` mid-sentence so it
        # doesn't dangle after the ``<pre>`` block, then wrap the address itself.
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
