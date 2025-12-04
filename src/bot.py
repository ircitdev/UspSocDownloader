"""Bot initialization and setup module."""
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
import logging
from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def setup_bot_commands(bot: Bot) -> None:
    """Setup bot commands.

    Args:
        bot: Bot instance
    """
    commands = [
        BotCommand(command="start", description="🚀 Start the bot"),
        BotCommand(command="help", description="❓ Show help"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands configured")


async def create_bot() -> tuple[Bot, Dispatcher]:
    """Create and configure bot instance.

    Returns:
        Tuple of (Bot, Dispatcher) instances
    """
    logger.info(f"Creating bot instance - {config.APP_NAME}")

    # Create bot instance
    bot = Bot(token=config.BOT_TOKEN)

    # Create storage and dispatcher
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Setup commands
    await setup_bot_commands(bot)

    logger.info("Bot and dispatcher created successfully")
    return bot, dp


async def close_bot(bot: Bot) -> None:
    """Close bot session.

    Args:
        bot: Bot instance
    """
    logger.info("Closing bot session")
    await bot.session.close()
