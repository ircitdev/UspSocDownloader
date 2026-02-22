"""Bot initialization and setup module."""
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage
import logging
from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def setup_bot_commands(bot: Bot) -> None:
    """Setup bot commands for users and admin.

    Args:
        bot: Bot instance
    """
    # Команды для всех пользователей
    user_commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="help", description="❓ Справка по боту"),
        BotCommand(command="stats", description="📊 Моя статистика"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="ref", description="🔗 Реферальная ссылка"),
    ]
    
    # Дополнительные команды для админа
    admin_commands = user_commands + [
        BotCommand(command="admin", description="👑 Админ-панель"),
        BotCommand(command="broadcast", description="📢 Рассылка всем"),
        BotCommand(command="allstats", description="📈 Общая статистика"),
        BotCommand(command="users", description="👥 Список пользователей"),
    ]
    
    # Устанавливаем команды для всех
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    logger.info("User commands configured")
    
    # Устанавливаем расширенные команды для админа
    try:
        await bot.set_my_commands(
            admin_commands, 
            scope=BotCommandScopeChat(chat_id=config.ADMIN_ID)
        )
        logger.info(f"Admin commands configured for user {config.ADMIN_ID}")
    except Exception as e:
        logger.warning(f"Failed to set admin commands: {e}")


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
