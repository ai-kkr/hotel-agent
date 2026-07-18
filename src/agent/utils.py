"""Agent-side delivery helper: send a message to the guest's Telegram chat.

Lives in the agent layer (not ``src.temporal``) so agent tools can import it directly without
crossing into the Temporal package — keeping the dependency direction one-way (temporal/bot depend
on agent, never the reverse). The Telegram bot and the HTML renderer are imported lazily inside the
call, so importing this module pulls in neither ``src.bot.app`` (→ bot core → agent stream →
temporal client) nor anything else that would cycle back through ``src.agent`` during package init.
"""

from langgraph.runtime import Runtime, get_runtime

from .context import EmailContext


async def send_telegram_reply(content: str) -> None:
    """Send ``content`` to the guest's Telegram chat, substituting ``$user_inbox``.

    The Telegram chat id and the client's forwarding inbox (``reply_to``) are read from the current
    LangGraph runtime context (:class:`EmailContext`), so this must be called from within a node/tool
    execution. The bot and the HTML renderer are imported lazily — see the module docstring.
    """
    from src.bot.app import get_bot
    from src.bot.utils import send_formatted

    runtime: Runtime[EmailContext] = get_runtime()  # ty:ignore[invalid-type-arguments]
    if telegram_id := runtime.context.get("telegram_id"):
        # ``reply_to`` carries the client's forwarding inbox (= ``$user_inbox``); pass it so the
        # placeholder in the agent's text is substituted when rendered to chat.
        inbox = runtime.context.get("reply_to") or ""
        await send_formatted(get_bot(), telegram_id, content, inbox=inbox)
