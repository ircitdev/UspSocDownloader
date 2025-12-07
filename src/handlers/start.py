"""Handler for /start command."""
from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from src.utils.logger import get_logger
from src.localization.messages import START_WELCOME
from src.utils.sheets import sheets_manager
from src.utils.notifications import notification_manager

logger = get_logger(__name__)
router = Router()

# Хранилище для отслеживания новых пользователей (для уведомлений)
known_users = set()


@router.message(CommandStart())
async def start_command(message: types.Message) -> None:
    """Handle /start command with referral support.

    Args:
        message: Telegram message object
    """
    user = message.from_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    is_premium = user.is_premium or False
    language = user.language_code

    # Извлекаем referrer_id из deep link (например /start ref_123456)
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith("ref_"):
            try:
                referrer_id = int(param[4:])
            except ValueError:
                pass

    logger.info(f"User {user_id} (@{username}) started bot" +
                (f" with referrer {referrer_id}" if referrer_id else ""))

    try:
        # Регистрируем/обновляем пользователя в Google Sheets
        await sheets_manager.register_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
            is_premium=is_premium,
            referrer_id=referrer_id
        )

        # Отправляем уведомление о новом пользователе (только первый раз)
        if user_id not in known_users:
            known_users.add(user_id)
            await notification_manager.notify_new_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_premium=is_premium,
                referrer_id=referrer_id
            )

        # Отправляем приветственное сообщение
        await message.answer(START_WELCOME)
        logger.debug(f"Welcome message sent to {user_id}")

    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        # Всё равно отправляем приветствие
        try:
            await message.answer(START_WELCOME)
        except:
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
