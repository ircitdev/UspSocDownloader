"""
Handler для обработки сообщений с URL
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from src.utils.logger import get_logger
from src.processors.url_processor import URLProcessor, Platform
from src.utils.validators import MessageValidator
from src.localization.messages import (
    INVALID_MESSAGE, UNSUPPORTED_PLATFORM, PLATFORMS, CONTENT_TYPES
)

logger = get_logger(__name__)
router = Router()

url_processor = URLProcessor()


@router.message(F.text.regexp(r'https?://'))
async def handle_url_message(message: types.Message):
    """Обрабатывает сообщения с URL"""
    try:
        # Валидируем сообщение и извлекаем URL
        is_valid, urls, error = MessageValidator.validate_and_extract_urls(message.text)

        if not is_valid:
            logger.info(f"User {message.from_user.id}: Invalid message - {error}")
            await message.answer(INVALID_MESSAGE)
            return

        # Обрабатываем каждый найденный URL
        for url in urls:
            url_info = url_processor.process(url)

            if not url_info.is_valid:
                logger.warning(
                    f"User {message.from_user.id}: Invalid URL - {url_info.error_message}"
                )
                await message.answer(f"❌ {url_info.error_message}\n\nСсылка: `{url}`", parse_mode="Markdown")
                continue

            # Определяем платформу
            platform_emoji, platform_name = PLATFORMS.get(
                url_info.platform.value,
                ("🔗", "Unknown")
            )

            content_type_text = CONTENT_TYPES.get(url_info.content_type, "контент")

            response_text = (
                f"{platform_emoji} *Найдена ссылка на {platform_name}*\n\n"
                f"*Тип контента:* {content_type_text}\n"
                f"*ID поста:* `{url_info.post_id}`\n\n"
                f"⏳ Сейчас начну загрузку...\n"
                f"(Загрузка на этом этапе не поддерживается)"
            )

            logger.info(
                f"User {message.from_user.id}: Detected {platform_name} URL "
                f"(type: {url_info.content_type}, id: {url_info.post_id})"
            )

            await message.answer(response_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error handling URL message from user {message.from_user.id}: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при обработке ссылки.\n"
            "Пожалуйста, попробуйте еще раз или используйте /help"
        )
