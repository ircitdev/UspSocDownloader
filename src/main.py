"""Main application module - Bot entry point."""
import asyncio
import logging
from src.utils.logger import get_logger
from src.bot import create_bot, close_bot
from src.config import config
from src.handlers import start, help, url_handler

logger = get_logger(__name__)

# Global bot reference for signal handlers
_bot = None


async def main() -> None:
    """Main async function - starts the bot."""
    global _bot

    logger.info("=" * 60)
    logger.info(f"Starting {config.APP_NAME}")
    logger.info("=" * 60)
    logger.debug(f"Debug mode: {config.DEBUG}")
    logger.debug(f"Log level: {config.LOG_LEVEL}")

    bot = None
    try:
        # Create bot instance
        bot, dp = await create_bot()
        _bot = bot

        # Register routers
        dp.include_router(start.router)
        dp.include_router(help.router)
        dp.include_router(url_handler.router)
        logger.info("Routers registered: /start, /help, URL handler")

        logger.info("Starting bot polling... (Press Ctrl+C to stop)")
        logger.info("=" * 60)

        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if bot:
            await close_bot(bot)
        logger.info("=" * 60)
        logger.info(f"{config.APP_NAME} stopped")
        logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Bot interrupted by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        raise
