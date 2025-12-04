"""Interactive test script - simulate user messages."""
import asyncio
from unittest.mock import AsyncMock, MagicMock
from aiogram import types
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger
from src.handlers import start, help as help_handler

logger = get_logger("test_handlers")


async def create_test_message(command: str, user_id: int = 123456789) -> types.Message:
    """Create mock Telegram message.

    Args:
        command: Command to simulate (/start or /help)
        user_id: User ID

    Returns:
        Mock Message object
    """
    message = AsyncMock(spec=types.Message)
    message.from_user = MagicMock()
    message.from_user.id = user_id
    message.bot = MagicMock()
    message.bot.first_name = "UspSocDownloader"
    message.answer = AsyncMock()
    return message


async def test_start_handler() -> bool:
    """Test /start command handler.

    Returns:
        True if test passed
    """
    try:
        logger.info("[TEST] Testing /start handler...")
        message = await create_test_message("/start")

        await start.start_command(message)

        # Verify answer was called
        if not message.answer.called:
            logger.error("[FAIL] start_command did not call message.answer()")
            return False

        # Get the response text
        call_args = message.answer.call_args
        response_text = call_args[0][0] if call_args[0] else ""

        if not response_text:
            logger.error("[FAIL] start_command sent empty message")
            return False

        logger.info(f"[OK] /start handler works correctly")
        logger.debug(f"Response preview: {response_text[:100]}...")
        return True

    except Exception as e:
        logger.error(f"[FAIL] /start handler test failed: {e}", exc_info=True)
        return False


async def test_help_handler() -> bool:
    """Test /help command handler.

    Returns:
        True if test passed
    """
    try:
        logger.info("[TEST] Testing /help handler...")
        message = await create_test_message("/help")

        await help_handler.help_command(message)

        # Verify answer was called
        if not message.answer.called:
            logger.error("[FAIL] help_command did not call message.answer()")
            return False

        # Get the response text
        call_args = message.answer.call_args
        response_text = call_args[0][0] if call_args[0] else ""

        if not response_text:
            logger.error("[FAIL] help_command sent empty message")
            return False

        logger.info(f"[OK] /help handler works correctly")
        logger.debug(f"Response preview: {response_text[:100]}...")
        return True

    except Exception as e:
        logger.error(f"[FAIL] /help handler test failed: {e}", exc_info=True)
        return False


async def main() -> None:
    """Run all handler tests."""
    logger.info("=" * 60)
    logger.info("Testing Bot Handlers")
    logger.info("=" * 60)
    logger.info("")

    results = {
        "/start": await test_start_handler(),
        "/help": await test_help_handler(),
    }

    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Results:")
    logger.info("=" * 60)

    all_passed = True
    for handler, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        logger.info(f"{status} {handler} handler")
        if not passed:
            all_passed = False

    logger.info("=" * 60)
    if all_passed:
        logger.info("[SUCCESS] All handler tests passed!")
    else:
        logger.error("[FAIL] Some tests failed!")
    logger.info("=" * 60)

    return all_passed


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted")
    except Exception as e:
        logger.critical(f"Test error: {e}", exc_info=True)
        sys.exit(1)
