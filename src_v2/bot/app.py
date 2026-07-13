from aiogram import Bot
from aiogram.types import BotCommand

from infrastructure.logging import get_logger
from src_v2.bot.core import dp

lg = get_logger(__name__)

# Command list shown as suggestions when the user types ``/`` and in the chat Menu.
# Registering these via setMyCommands is what makes Telegram surface them at all.
DEFAULT_COMMANDS = [
    BotCommand(command="start", description="Запустить / показать адрес для пересылки"),
]


async def run_bot(bot: Bot) -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    try:
        await bot.set_my_commands(DEFAULT_COMMANDS)
        await dp.start_polling(bot)
    except Exception as e:
        lg.exception("Bot polling failed", error=str(e))
