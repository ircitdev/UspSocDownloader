"""
Handler для обработки сообщений с URL и загрузки медиа
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from src.utils.logger import get_logger
from src.processors.url_processor import URLProcessor, Platform
from src.downloaders.media_downloader import MediaDownloader
from src.utils.validators import MessageValidator
from src.localization.messages import (
    INVALID_MESSAGE, UNSUPPORTED_PLATFORM, PLATFORMS, CONTENT_TYPES
)

logger = get_logger(__name__)
router = Router()

url_processor = URLProcessor()
media_downloader = MediaDownloader()


@router.message(F.text.regexp(r'https?://'))
async def handle_url_message(message: types.Message):
    """Обрабатывает сообщения с URL и загружает медиа"""
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

            # Отправляем сообщение о начале загрузки
            status_msg = await message.answer(
                f"{platform_emoji} *Загрузка с {platform_name}...*\n\n"
                f"📝 Тип: {content_type_text}\n"
                f"⏳ Пожалуйста, подождите...",
                parse_mode="Markdown"
            )

            logger.info(
                f"User {message.from_user.id}: Starting download from {platform_name} "
                f"(type: {url_info.content_type}, id: {url_info.post_id})"
            )

            try:
                # Загружаем медиа
                download_result = await media_downloader.download(
                    url=url,
                    content_type=url_info.content_type,
                    platform=platform_name,
                )

                if download_result.success and download_result.file_path:
                    file_path = download_result.file_path
                    title = download_result.title or "Медиа"
                    file_size_mb = download_result.file_size / (1024 * 1024)

                    logger.info(
                        f"User {message.from_user.id}: Download successful ({file_size_mb:.1f} MB)"
                    )

                    # Формируем информацию
                    info_text = f"✅ *Загружено с {platform_name}*\n\n"
                    info_text += f"📝 {title}\n"
                    info_text += f"📊 Размер: {file_size_mb:.1f} MB"

                    if download_result.duration:
                        minutes = int(download_result.duration // 60)
                        seconds = int(download_result.duration % 60)
                        info_text += f"\n⏱️ Длительность: {minutes}:{seconds:02d}"

                    # Удаляем статус
                    try:
                        await status_msg.delete()
                    except:
                        pass

                    # Отправляем файл
                    try:
                        if url_info.content_type in ["video", "reel", "shorts", "clip"]:
                            await message.answer_video(
                                types.FSInputFile(file_path),
                                caption=info_text,
                                parse_mode="Markdown"
                            )
                        elif url_info.content_type == "audio":
                            await message.answer_audio(
                                types.FSInputFile(file_path),
                                title=title,
                                caption=info_text,
                                parse_mode="Markdown"
                            )
                        elif url_info.content_type == "photo":
                            await message.answer_photo(
                                types.FSInputFile(file_path),
                                caption=info_text,
                                parse_mode="Markdown"
                            )
                        else:
                            await message.answer_document(
                                types.FSInputFile(file_path),
                                caption=info_text,
                                parse_mode="Markdown"
                            )

                        logger.info(f"User {message.from_user.id}: File sent successfully")

                    except Exception as e:
                        logger.error(f"Error sending file: {str(e)}")
                        await message.answer(
                            f"⚠️ Файл загружен, но не удалось отправить\n"
                            f"Ошибка: {str(e)[:100]}"
                        )

                else:
                    # Ошибка загрузки
                    error_msg = download_result.error_message or "Неизвестная ошибка"
                    logger.warning(f"User {message.from_user.id}: Download failed - {error_msg}")

                    try:
                        await status_msg.delete()
                    except:
                        pass

                    await message.answer(
                        f"❌ *Не удалось загрузить*\n\n"
                        f"Платформа: {platform_name}\n"
                        f"Ошибка: {error_msg}",
                        parse_mode="Markdown"
                    )

            except Exception as e:
                logger.error(f"Error in download process: {str(e)}")
                try:
                    await status_msg.delete()
                except:
                    pass
                await message.answer(f"❌ Ошибка загрузки: {str(e)[:100]}")

    except Exception as e:
        logger.error(f"Error handling URL message from user {message.from_user.id}: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при обработке ссылки.\n"
            "Пожалуйста, попробуйте еще раз или используйте /help"
        )
