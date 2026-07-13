from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import ErrorEvent, Message
from aiogram.utils.text_decorations import html_decoration

from src.agent.stream import stream_graph
from src.bot.templates import GREETING_TPL
from src.context import get_context
from src.db.models import ClientORM
from src.db.repositories import ClientRepository
from src.db.session import session_context
from src.logging import get_logger

dp = Dispatcher()
log = get_logger(__name__)


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
            await repo.add_client(telegram_id=message.from_user.id)

    await message.answer(
        text=GREETING_TPL.render(
            inbox_address=html_decoration.quote(client.inbox or "" if client else ""),
        ),
    )


@dp.message(Command("new"))
async def command_new_handler(message: Message) -> None:
    """Reset the agent's conversation memory for the current client.

    Deletes every checkpointed message and state value for the client's thread
    (``AsyncPostgresSaver.adelete_thread``), so the next message starts a blank conversation with
    no prior context — booking details, wishes, hotel-threading state, message history, everything.

    Registered before ``chat_handler``: aiogram dispatches to the first matching handler, and
    ``"/new"`` also matches ``F.text``, so order matters. The ``outbound_emails`` rows live in
    Postgres (not the checkpoint), so a delayed hotel reply still routes correctly — into the now
    empty thread.
    """
    assert message.from_user is not None, "message.from_user is None"
    ctx = get_context()
    async with session_context(ctx.session_factory) as session:
        repo = ClientRepository(session)
        client: ClientORM | None = await repo.get_client_by_telegram_id(message.from_user.id)

    if client is not None:
        saver = ctx.checkpoint_saver
        assert saver is not None, "checkpoint_saver is not initialized"
        await saver.adelete_thread(thread_id=client.thread_id)
        log.info("bot.session_reset", client_id=client.id, thread_id=client.thread_id)

    await message.answer("Контекст сброшен — начинаем с чистого листа.")


@dp.message(F.text)
async def chat_handler(message: Message) -> None:
    """Forward free-form chat messages to the hotel-conversation agent.

    Registered after ``command_start_handler``: aiogram dispatches to the first matching handler,
    so ``/start`` is handled there and never reaches this one. Any other text goes to the agent.
    Commands we do not recognise are ignored here rather than forwarded.

    The agent thread is keyed by the client (``ClientORM.thread_id``); :func:`stream_graph` and the
    agent handle both fresh turns and resuming an ``interrupt`` (e.g. ``ask_user`` awaiting the
    user's reply). Streamed agent output is delivered back to the chat inside ``stream_graph``.
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
            client = await repo.add_client(telegram_id=message.from_user.id)

    await stream_graph(
        msg=message.text,
        client=client,
    )
