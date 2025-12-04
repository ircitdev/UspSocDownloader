"""
Download Handler - обработка команды загрузки медиа
"""
import os
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.utils.logger import get_logger
from src.processors.url_processor import URLProcessor, Platform
from src.downloaders.media_downloader import MediaDownloader
from src.utils.validators import MessageValidator
from src.localization.messages import (
    INVALID_MESSAGE, PLATFORMS, CONTENT_TYPES,
    DOWNLOAD_SUCCESS, DOWNLOAD_ERROR, FILE_SEND_ERROR, INFO_DURATION
)

logger = get_logger(__name__)
router = Router()

url_processor = URLProcessor()
media_downloader = MediaDownloader()


class DownloadStates(StatesGroup):
    """Состояния для процесса загрузки"""
    waiting_for_url = State()
    downloading = State()


@router.message()
async def handle_download_message(message: types.Message, state: FSMContext):
    """Обрабатывает сообщения с ссылками и инициирует загрузку"""
    try:
        # Валидируем сообщение и извлекаем URL
        is_valid, urls, error = MessageValidator.validate_and_extract_urls(message.text)

        if not is_valid:
            logger.info(f"User {message.from_user.id}: Invalid message - {error}")
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

            # Проверяем поддержку загрузки
            if url_info.platform not in [
                Platform.INSTAGRAM,
                Platform.YOUTUBE,
                Platform.TIKTOK,
                Platform.VK,
                Platform.X,
            ]:
                await message.answer(f"❌ Загрузка с этой платформы не поддерживается")
                continue

            # Отправляем сообщение о начале загрузки
            download_msg = f"{platform_emoji} *Загрузка контента...*\n\nПлатформа: {platform_name}\n📝 Тип: {content_type_text}\n\n⏳ Пожалуйста, подождите..."
            status_msg = await message.answer(download_msg, parse_mode="Markdown")

            logger.info(
                f"User {message.from_user.id}: Starting download from {platform_name} "
                f"(type: {url_info.content_type})"
            )

            try:
                # Загружаем медиа
                download_result = await media_downloader.download(
                    url=url,
                    content_type=url_info.content_type,
                    platform=platform_name,
                )

                if download_result.success:
                    # Отправляем скачанный файл
                    file_path = download_result.file_path
                    title = download_result.title or "Медиа"
                    file_size_mb = download_result.file_size / (1024 * 1024)

                    logger.info(
                        f"User {message.from_user.id}: Download successful "
                        f"({file_size_mb:.1f} MB)"
                    )

                    # Формируем сообщение с информацией
                    info_text = "✅ *Загрузка успешна!*\n\n"
                    info_text += f"📝 Название: {title}\n"
                    info_text += f"📊 Размер: {file_size_mb:.1f} MB\n"

                    if download_result.duration:
                        minutes = int(download_result.duration // 60)
                        seconds = int(download_result.duration % 60)
                        info_text += f"⏱️ Длительность: {minutes}:{seconds:02d}\n"

                    info_text += f"🔗 Платформа: {platform_name}"

                    # Отправляем информацию
                    await message.answer(info_text, parse_mode="Markdown")

                    # Отправляем файл в зависимости от типа
                    try:
                        with open(file_path, "rb") as file:
                            if url_info.content_type in ["video", "reel", "shorts"]:
                                await message.answer_video(
                                    types.FSInputFile(file_path),
                                    caption=f"📥 {title}",
                                )
                            elif url_info.content_type in ["audio"]:
                                await message.answer_audio(
                                    types.FSInputFile(file_path),
                                    title=title,
                                )
                            else:
                                await message.answer_document(
                                    types.FSInputFile(file_path),
                                    caption=title,
                                )

                        logger.info(f"User {message.from_user.id}: File sent successfully")

                    except Exception as e:
                        logger.error(f"Error sending file: {str(e)}")
                        await message.answer(
                            f"⚠️ Файл загружен но не удалось отправить\n"
                            f"Ошибка: {str(e)[:100]}"
                        )

                else:
                    # Ошибка при загрузке
                    error_msg = download_result.error_message or "Неизвестная ошибка"
                    logger.warning(
                        f"User {message.from_user.id}: Download failed - {error_msg}"
                    )

                    await message.answer(
                        f"❌ Не удалось загрузить контент\n\n"
                        f"Ошибка: {error_msg}",
                    )

            except Exception as e:
                logger.error(f"Error in download process: {str(e)}")
                await message.answer(
                    f"❌ Ошибка при загрузке\n\n"
                    f"Детали: {str(e)[:100]}"
                )
            finally:
                # Удаляем сообщение статуса
                try:
                    await status_msg.delete()
                except:
                    pass

    except Exception as e:
        logger.error(f"Error handling download message: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при обработке ссылки.\n"
            "Пожалуйста, попробуйте еще раз или используйте /help"
        )
