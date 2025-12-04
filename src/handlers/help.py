"""Handler for /help command."""
from aiogram import Router, types
from aiogram.filters import Command
from src.utils.logger import get_logger
from src.localization.messages import HELP_TEXT

logger = get_logger(__name__)
router = Router()


@router.message(Command("help"))
async def help_command(message: types.Message) -> None:
    """Handle /help command.

    Args:
        message: Telegram message object
    """
    logger.info(f"User {message.from_user.id} requested help")

    try:
        await message.answer(HELP_TEXT, parse_mode="Markdown")
        logger.debug(f"Help message sent to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error sending help message: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
