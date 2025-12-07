"""Main application module - Bot entry point."""
import asyncio
import logging
from src.utils.logger import get_logger
from src.bot import create_bot, close_bot
from src.config import config
from src.handlers import start, help as help_handler, url_handler, commands
from src.utils.notifications import notification_manager
from src.utils.sheets import sheets_manager

logger = get_logger(__name__)


async def main():
    """Main async function - starts the bot."""
    logger.info(f"Starting {config.APP_NAME}")
    logger.debug(f"Debug mode: {config.DEBUG}")

    bot = None
    try:
        # Create bot instance
        bot, dp = await create_bot()

        # Initialize notification manager with bot instance
        notification_manager.set_bot(bot)
        logger.info("Notification manager initialized")

        # Initialize Google Sheets connection
        if await sheets_manager.init():
            logger.info("Google Sheets connected")
        else:
            logger.warning("Google Sheets not available - stats will not be recorded")

        # Register routers
        dp.include_router(start.router)
        dp.include_router(help_handler.router)
        dp.include_router(url_handler.router)
        dp.include_router(commands.router)
        logger.info("Routers registered: start, help, url_handler")

        logger.info("Starting bot polling...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if bot:
            await close_bot(bot)
        logger.info(f"{config.APP_NAME} stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        raise
