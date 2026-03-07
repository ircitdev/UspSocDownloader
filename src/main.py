"""Main application module - Bot entry point."""
import asyncio
import subprocess
import sys
import logging
from src.utils.logger import get_logger
from src.bot import create_bot, close_bot
from src.config import config
from src.handlers import start, help, url_handler, commands
from src.utils.notifications import notification_manager
from src.utils.sheets import sheets_manager
from src.database.db_manager import init_database

logger = get_logger(__name__)


def update_ytdlp() -> None:
    """Update yt-dlp to the latest version."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "--quiet"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            import yt_dlp
            logger.info(f"yt-dlp updated successfully: {yt_dlp.version.__version__}")
        else:
            logger.warning(f"yt-dlp update failed: {result.stderr[:200]}")
    except Exception as e:
        logger.warning(f"yt-dlp auto-update error: {e}")


async def auto_update_ytdlp_loop() -> None:
    """Check and update yt-dlp every 24 hours."""
    while True:
        await asyncio.sleep(24 * 60 * 60)
        logger.info("Running scheduled yt-dlp update...")
        await asyncio.get_event_loop().run_in_executor(None, update_ytdlp)

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

    # Update yt-dlp at startup
    logger.info("Checking yt-dlp version...")
    await asyncio.get_event_loop().run_in_executor(None, update_ytdlp)

    bot = None
    try:
        # Initialize database
        init_database(config.DATABASE_PATH)
        logger.info(f"Database initialized at {config.DATABASE_PATH}")

        # Create bot instance
        bot, dp = await create_bot()
        _bot = bot

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
        dp.include_router(help.router)
        dp.include_router(commands.router)
        dp.include_router(url_handler.router)
        logger.info("Routers registered: start, help, commands, url_handler")

        logger.info("Starting bot polling... (Press Ctrl+C to stop)")
        logger.info("=" * 60)

        # Start background yt-dlp auto-update (every 24h)
        asyncio.create_task(auto_update_ytdlp_loop())

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
