"""Main application module - Bot entry point."""
import asyncio
import subprocess
import sys
import logging
from src.utils.logger import get_logger
from src.bot import create_bot, close_bot
from src.config import config
from src.handlers import start, help as help_handler, url_handler, commands
from src.utils.notifications import notification_manager
from src.utils.sheets import sheets_manager
from src.downloaders.media_downloader import media_downloader
from src.utils.instagram_health import instagram_health
from src.database.db_manager import init_database
from src.utils.file_cleaner import init_cleanup_service

logger = get_logger(__name__)


def update_ytdlp() -> None:
    """Update yt-dlp to the latest version."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "--quiet"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            import yt_dlp
            logger.info(f"yt-dlp updated: {yt_dlp.version.__version__}")
        else:
            logger.warning(f"yt-dlp update failed: {result.stderr[:200]}")
    except Exception as e:
        logger.warning(f"yt-dlp auto-update error: {e}")


async def auto_update_ytdlp_loop(bot=None) -> None:
    """Check and update yt-dlp every 24 hours."""
    while True:
        await asyncio.sleep(24 * 60 * 60)
        logger.info("Running scheduled yt-dlp update...")
        try:
            import importlib
            _ytv = importlib.import_module("yt_dlp.version")
            old_version = _ytv.__version__
        except Exception:
            old_version = None
        await asyncio.get_event_loop().run_in_executor(None, update_ytdlp)
        if bot:
            try:
                import importlib
                _ytv2 = importlib.import_module("yt_dlp.version")
                importlib.reload(_ytv2)
                new_version = _ytv2.__version__
                if old_version and old_version != new_version:
                    msg = f"🔄 <b>yt-dlp обновлён</b>\n\n{old_version} → <b>{new_version}</b>"
                else:
                    msg = f"✅ <b>yt-dlp актуален</b>: {new_version}"
                await bot.send_message(chat_id=config.ADMIN_ID, text=msg, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Failed to notify admin about yt-dlp update: {e}")


async def main():
    """Main async function - starts the bot."""
    logger.info(f"Starting {config.APP_NAME}")
    logger.debug(f"Debug mode: {config.DEBUG}")

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

        # Initialize notification manager with bot instance
        notification_manager.set_bot(bot)
        logger.info("Notification manager initialized")

        # Initialize Instagram health checker
        instagram_health.set_bot(bot)
        instagram_health.start()
        logger.info("Instagram health checker started (12h interval)")

        # Initialize file cleanup service
        cleanup_service = init_cleanup_service(cleanup_interval_hours=6)
        await cleanup_service.start()
        logger.info("File cleanup service started (6h interval)")

        # Initialize Google Sheets connection
        if await sheets_manager.init():
            logger.info("Google Sheets connected")
        else:
            logger.warning("Google Sheets not available - stats will not be recorded")

        # Register routers
        dp.include_router(start.router)
        dp.include_router(help_handler.router)
        dp.include_router(commands.router)
        dp.include_router(url_handler.router)
        logger.info("Routers registered: start, help, commands, url_handler")

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

        # Start background yt-dlp auto-update (every 24h)
        asyncio.create_task(auto_update_ytdlp_loop(bot))

        # Notify admin about bot startup
        try:
            import importlib
            _ytv = importlib.import_module("yt_dlp.version")
            ytdlp_ver = _ytv.__version__
        except Exception:
            ytdlp_ver = "unknown"
        try:
            await bot.send_message(
                chat_id=config.ADMIN_ID,
                text=f"🚀 <b>{config.APP_NAME} запущен</b>\n\n🔧 yt-dlp: {ytdlp_ver}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin about startup: {e}")

        logger.info("Starting bot polling...")
        await dp.start_polling(bot)

        # Cancel cleanup task on shutdown
        cleanup_task.cancel()
        instagram_health.stop()
        await cleanup_service.stop()
        logger.info("File cleanup service stopped")

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
