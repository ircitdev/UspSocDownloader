"""Handler for /help command."""
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from src.utils.logger import get_logger
from src.localization.messages import HELP_TEXT

logger = get_logger(__name__)
router = Router()


@router.message(Command("help"))
async def help_command(message: types.Message) -> None:
    """Handle /help command.

    Args:
        message: Telegram message object
    """
    logger.info(f"User {message.from_user.id} requested help")

    try:
        await message.answer(HELP_TEXT, parse_mode="Markdown")
        logger.debug(f"Help message sent to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error sending help message: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(Command("howto"))
async def howto_command(message: types.Message) -> None:
    """Handle /howto command - opens web documentation in Telegram Mini App.

    Args:
        message: Telegram message object
    """
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested howto (Mini App)")

    try:
        # Create inline keyboard with Web App button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 Открыть руководство",
                    web_app=WebAppInfo(url="https://socdownloader.tools.uspeshnyy.ru")
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Поддержка",
                    url="https://t.me/smit_support"
                )
            ]
        ])

        await message.answer(
            "📚 <b>Интерактивное руководство</b>\n\n"
            "Нажмите кнопку ниже, чтобы открыть полное интерактивное руководство "
            "по использованию бота прямо в Telegram!\n\n"
            "Вы найдёте:\n"
            "• 🚀 Инструкции по началу работы\n"
            "• 📱 Список поддерживаемых платформ\n"
            "• ✨ Описание всех возможностей\n"
            "• ⚡ Список команд с примерами\n"
            "• 🤖 Гайд по AI-функциям\n"
            "• ❓ Ответы на частые вопросы",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        logger.debug(f"Howto Mini App link sent to {user_id}")

    except Exception as e:
        logger.error(f"Error sending howto message: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
