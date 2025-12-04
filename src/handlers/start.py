"""Handler for /start command."""
from aiogram import Router, types
from aiogram.filters import Command
from src.utils.logger import get_logger
from src.localization.messages import START_WELCOME

logger = get_logger(__name__)
router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message) -> None:
    """Handle /start command.

    Args:
        message: Telegram message object
    """
    logger.info(f"User {message.from_user.id} started bot")

    try:
        await message.answer(START_WELCOME)
        logger.debug(f"Welcome message sent to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
