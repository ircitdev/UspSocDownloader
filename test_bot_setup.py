"""Test script - test bot commands without running polling."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger
from src.config import config

logger = get_logger("test_bot")


async def test_imports() -> bool:
    """Test all imports work correctly.

    Returns:
        True if all imports successful
    """
    try:
        logger.info("Testing imports...")

        from src.bot import create_bot
        logger.info("[OK] Bot module imported")

        from src.handlers import start, help
        logger.info("[OK] Handlers imported")

        from src.config import config
        logger.info(f"[OK] Config loaded: {config}")

        return True
    except Exception as e:
        logger.error(f"Import test failed: {e}", exc_info=True)
        return False


async def test_bot_creation() -> bool:
    """Test bot creation.

    Returns:
        True if bot created successfully
    """
    try:
        logger.info("Testing bot creation...")

        from src.bot import create_bot, close_bot
        bot, dp = await create_bot()

        logger.info(f"[OK] Bot created: {bot}")
        logger.info(f"[OK] Dispatcher created: {dp}")

        # Get bot info
        me = await bot.get_me()
        logger.info(f"[OK] Bot info: {me.username} (@{me.username})")

        await close_bot(bot)
        logger.info("[OK] Bot closed successfully")

        return True
    except Exception as e:
        logger.error(f"Bot creation test failed: {e}", exc_info=True)
        return False


async def main() -> None:
    """Run tests."""
    logger.info("=" * 60)
    logger.info("Starting Bot Tests")
    logger.info("=" * 60)

    # Test imports
    if not await test_imports():
        logger.error("[FAIL] Import test failed!")
        return

    logger.info("")

    # Test bot creation
    if not await test_bot_creation():
        logger.error("[FAIL] Bot creation test failed!")
        return

    logger.info("")
    logger.info("=" * 60)
    logger.info("[SUCCESS] All tests passed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests interrupted")
    except Exception as e:
        logger.critical(f"Test error: {e}", exc_info=True)
