from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import ErrorEvent, Message
from aiogram.utils.text_decorations import html_decoration
from langchain_core.messages import HumanMessage

from src.bot.templates import GREETING_TPL
from src.context import get_context
from src.db.models import ClientORM
from src.db.repositories import ClientRepository
from src.db.session import session_context
from src.logging import get_logger
from src.temporal.client import agent_step

dp = Dispatcher()
log = get_logger(__name__)


def build_now_context(when_utc: datetime, home_tz: str | None, trip_tz: str | None) -> str:
    """Render a one-line current-time context for the client, to stamp onto the incoming message.

    Shows the moment the guest wrote (``when_utc`` — always UTC from Telegram) in UTC plus the two
    scheduling zones when they're set, so the agent can interpret "today / tomorrow / in 3 days"
    and reason about home-vs-trip without guessing a timezone. Goes into the human message (the
    request tail) — never the prefix — so it doesn't bust the LLM prefix cache.
    """
    parts = [f"UTC {when_utc.strftime('%Y-%m-%d %H:%M')}"]
    for label, tz in (("дом", home_tz), ("поездка", trip_tz)):
        if tz:
            try:
                local = when_utc.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")
            except Exception:
                continue  # bad zone — shouldn't happen (validated at set_booking_info); skip silently
            parts.append(f"{label} ({tz}) {local}")
    return "[текущее время клиента — " + " | ".join(parts) + "]"


@dp.errors()
async def on_error(event: ErrorEvent) -> None:
    """Surface handler exceptions instead of letting aiogram swallow them silently."""
    log.exception(
        "bot.handler_error",
        error=str(event.exception),
        update_id=getattr(event.update, "update_id", None),
        exc_info=event.exception,
    )


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`

    ctx = get_context()
    assert message.from_user is not None, "message.from_user is None"
    async with session_context(ctx.session_factory) as session:
        repo = ClientRepository(session)
        client: ClientORM | None = await repo.get_client_by_telegram_id(message.from_user.id)
        if client is None:
            client = await repo.add_client(telegram_id=message.from_user.id)

    await message.answer(
        text=GREETING_TPL.render(
            inbox_address=html_decoration.quote(client.inbox or "" if client else ""),
        ),
    )


@dp.message(Command("new"))
async def command_new_handler(message: Message) -> None:
    """Reset the agent's conversation memory for the current client.

    Deletes the persisted agent state row for the client (``states`` table, keyed on ``client.id``)
    AND cancels every scheduled task the client has (Temporal schedule + ``scheduled_tasks`` catalog
    row), so the next message starts a truly blank slate — no prior context AND no pending task
    firing into the now-empty context.

    Registered before ``chat_handler``: aiogram dispatches to the first matching handler, and
    ``"/new"`` also matches ``F.text``, so order matters. The ``outbound_emails`` rows live in
    Postgres (not the agent state), so a delayed hotel reply still routes correctly — into the now
    empty state.
    """
    assert message.from_user is not None, "message.from_user is None"
    ctx = get_context()
    client_id: int | None = None
    async with session_context(ctx.session_factory) as session:
        repo = ClientRepository(session)
        # Resolve the client by Telegram id, then delete by the DB client.id — the ``states`` row is
        # keyed on clients.id (primary-key FK), NOT on the Telegram id; those are different values.
        client = await repo.get_client_by_telegram_id(message.from_user.id)
        if client is not None:
            client_id = client.id
            await repo.delete_state_by_client_id(client.id)

    cancelled = await cancel_all_scheduled_tasks(client_id) if client_id is not None else 0
    text = "Контекст сброшен — начинаем с чистого листа."
    if cancelled:
        text += f" Отменено запланированных задач: {cancelled}."
    await message.answer(text)


async def cancel_all_scheduled_tasks(client_id: int) -> int:
    """Cancel every scheduled task for ``client_id`` — Temporal schedule + DB catalog row.

    Used by ``/new`` for a clean slate. Temporal-first per task (same ordering as the cancel tool):
    a crash between the Temporal delete and the catalog delete leaves at worst a stale row, never an
    uncancelled firing. Best-effort — a transient Temporal failure skips that task and leaves its
    catalog row tracked (and logged). Returns the number of tasks actually cancelled.
    """
    from src.db.repositories import ScheduledTaskRepository
    from src.db.session import session_context
    from src.temporal.schedules import delete as schedule_delete

    ctx = get_context()
    async with session_context(ctx.session_factory) as session:
        keys = await ScheduledTaskRepository(session).keys_for_client(client_id)

    cancelled: list[str] = []
    for key in keys:
        try:
            await schedule_delete(client_id=client_id, task_key=key)
        except Exception as exc:  # transient Temporal error — skip, keep the row tracked
            log.warning(
                "bot.schedule_cancel_failed", client_id=client_id, task_key=key, error=str(exc)
            )
            continue
        cancelled.append(key)

    if cancelled:
        async with session_context(ctx.session_factory) as session:
            repo = ScheduledTaskRepository(session)
            for key in cancelled:
                await repo.delete(client_id, key)
    return len(cancelled)


@dp.message(F.text)
async def chat_handler(message: Message) -> None:
    """Forward free-form chat messages to the hotel-conversation agent.

    Registered after ``command_start_handler``: aiogram dispatches to the first matching handler,
    so ``/start`` is handled there and never reaches this one. Any other text goes to the agent.
    Commands we do not recognise are ignored here rather than forwarded.

    The turn is enqueued on the client's Temporal queue (:func:`agent_step`) and the handler
    returns immediately — the agent runs asynchronously and pushes its reply (and the "typing…"
    indicator) back to the chat via its activities. Do NOT await a result here: the handler must
    free up so the bot can keep polling.
    """
    assert message.text is not None, "message.text is None"
    if message.text.startswith("/"):
        return  # unknown command — do not forward to the agent

    assert message.from_user is not None, "message.from_user is None"
    ctx = get_context()
    async with session_context(ctx.session_factory) as session:
        repo = ClientRepository(session)
        client: ClientORM | None = await repo.get_client_by_telegram_id(message.from_user.id)
        if client is None:
            # First contact without /start — register the client on the fly.
            client = await repo.add_client(
                telegram_id=message.from_user.id,
            )
        # Current time in the client's zones — stamped onto THIS message (the request tail, so it
        # doesn't bust the prefix cache) so the agent can interpret relative timing ("завтра",
        # "через 3 дня") and reason about home vs trip. ``message.date`` is the UTC send time.
        home_tz, trip_tz = await repo.get_timezones(client.id)

    now_ctx = build_now_context(message.date or datetime.now(UTC), home_tz, trip_tz)
    await agent_step(
        update={"messages": [HumanMessage(content=f"{now_ctx}\n{message.text}")]},
        client=client,
    )
