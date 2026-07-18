from aiogram import Bot
from aiogram.types import BotCommand

from src.bot.core import dp
from src.context import get_context
from src.logging import get_logger

lg = get_logger(__name__)

# Command list shown as suggestions when the user types ``/`` and in the chat Menu.
# Registering these via setMyCommands is what makes Telegram surface them at all.
DEFAULT_COMMANDS = [
    BotCommand(command="start", description="Запустить / показать адрес для пересылки"),
    BotCommand(command="new", description="Сбросить контекст, начать заново"),
]


def get_bot() -> Bot:
    """Get the global bot instance for sending messages."""
    ctx = get_context()
    return ctx.bot


async def run_bot() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    try:
        bot = get_bot()
        await bot.set_my_commands(DEFAULT_COMMANDS)
        await dp.start_polling(bot)
    except Exception as e:
        lg.exception("Bot polling failed", error=str(e))
