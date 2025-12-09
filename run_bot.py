"""Main application module - Bot entry point."""
import asyncio
import logging
from src.utils.logger import get_logger
from src.bot import create_bot, close_bot
from src.config import config
from src.handlers import start, help as help_handler, url_handler, commands
from src.utils.notifications import notification_manager
from src.utils.sheets import sheets_manager
from src.downloaders.media_downloader import media_downloader
from src.utils.instagram_health import instagram_health

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

        # Initialize Instagram health checker
        instagram_health.set_bot(bot)
        instagram_health.start()
        logger.info("Instagram health checker started (12h interval)")

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

        # Cleanup old files on startup (keep for 1 day)
        media_downloader.cleanup_old_files(days=1)
        logger.info("Old files cleanup completed (keeping files for 1 day)")

        # Initial Instagram health check
        is_ok, msg = await instagram_health.run_check(notify_on_success=False)
        if is_ok:
            logger.info(f"Instagram health: OK")
        else:
            logger.warning(f"Instagram health: {msg}")

        # Start periodic cleanup task (every hour)
        async def periodic_cleanup():
            while True:
                await asyncio.sleep(3600)  # 1 hour
                media_downloader.cleanup_old_files(days=1)
                logger.info("Periodic cleanup completed")
        
        cleanup_task = asyncio.create_task(periodic_cleanup())

        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
        
        # Cancel cleanup task on shutdown
        cleanup_task.cancel()
        instagram_health.stop()

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
