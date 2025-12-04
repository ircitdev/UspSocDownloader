"""Main application module - Bot entry point."""
import asyncio
import logging
from src.utils.logger import get_logger
from src.bot import create_bot, close_bot
from src.config import config
from src.handlers import start, help as help_handler

logger = get_logger(__name__)


async def main():
    """Main async function - starts the bot."""
    logger.info(f"Starting {config.APP_NAME}")
    logger.debug(f"Debug mode: {config.DEBUG}")

    try:
        # Create bot instance
        bot, dp = await create_bot()

        # Register routers
        dp.include_router(start.router)
        dp.include_router(help_handler.router)

        logger.info("Starting bot polling...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
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
