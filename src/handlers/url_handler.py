"""
Handler для обработки сообщений с URL и загрузки медиа
"""
import time
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from src.utils.logger import get_logger
from src.processors.url_processor import URLProcessor, Platform
from src.downloaders.media_downloader import MediaDownloader
from src.utils.validators import MessageValidator
from src.utils.translator import (
    is_russian_text, translate_to_russian, rewrite_text,
    check_images_have_text, extract_text_from_images
)
from src.localization.messages import (
    INVALID_MESSAGE, UNSUPPORTED_PLATFORM, PLATFORMS, CONTENT_TYPES
)
from src.utils.sheets import sheets_manager
from src.config import config

# Лимит бесплатных скачиваний в сутки
FREE_DAILY_LIMIT = 10
from src.utils.notifications import notification_manager

logger = get_logger(__name__)
router = Router()

url_processor = URLProcessor()
media_downloader = MediaDownloader()

# Импортируем файловые кэши
from src.utils.cache import image_paths_cache, original_texts_cache

# Кэши для YouTube
youtube_urls_cache = {}  # message_id -> url
youtube_formats_cache = {}  # message_id -> {360: {...}, 480: {...}, ...}

# Кэш для больших файлов
large_files_cache = {}  # message_id -> {file_path, platform, user_id, ...}


@router.message(F.text.regexp(r'https?://'))
async def handle_url_message(message: types.Message):
    """Обрабатывает сообщения с URL и загружает медиа"""
    user = message.from_user
    user_id = user.id
    username = user.username

    try:
        # Валидируем сообщение и извлекаем URL
        is_valid, urls, error = MessageValidator.validate_and_extract_urls(message.text)

        if not is_valid:
            logger.info(f"User {user_id}: Invalid message - {error}")
            await message.answer(INVALID_MESSAGE)
            return

        # Проверка лимита для бесплатных пользователей
        is_premium_user = False
        daily_count = 0
        if user_id == config.ADMIN_ID:
            is_premium_user = True  # Админ всегда Premium
        else:
            is_premium_user = await sheets_manager.is_user_premium(user_id)
            if not is_premium_user:
                daily_count = await sheets_manager.get_user_daily_requests(user_id)
                if daily_count >= FREE_DAILY_LIMIT:
                    logger.info(f"User {user_id}: Daily limit reached ({daily_count}/{FREE_DAILY_LIMIT})")
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💎 Получить Premium", callback_data="show_premium")]
                    ])
                    await message.answer(
                        f"⚠️ <b>Достигнут дневной лимит</b>\n\n"
                        f"Вы использовали {daily_count} из {FREE_DAILY_LIMIT} бесплатных скачиваний сегодня.\n\n"
                        f"💎 Для снятия лимита получите Premium статус.\n"
                        f"Лимит обновится в полночь.",
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    return

        # Обрабатываем каждый найденный URL
        for url in urls:
            start_time = time.time()
            url_info = url_processor.process(url)

            if not url_info.is_valid:
                logger.warning(f"User {user_id}: Invalid URL - {url_info.error_message}")
                await message.answer(f"❌ {url_info.error_message}\n\nСсылка: `{url}`", parse_mode="Markdown")
                continue

            # Определяем платформу
            platform_emoji, platform_name = PLATFORMS.get(
                url_info.platform.value,
                ("🔗", "Unknown")
            )

            content_type_text = CONTENT_TYPES.get(url_info.content_type, "контент")

            # === YOUTUBE: Показываем кнопки выбора качества ===
            if url_info.platform == Platform.YOUTUBE:
                await handle_youtube_quality_selection(message, url, platform_emoji, platform_name, user_id, username)
                continue

            # Отправляем сообщение о начале загрузки
            status_msg = await message.answer(
                f"{platform_emoji} *Загрузка с {platform_name}...*\n\n"
                f"📝 Тип: {content_type_text}\n"
                f"⏳ Пожалуйста, подождите...",
                parse_mode="Markdown"
            )

            logger.info(
                f"User {user_id}: Starting download from {platform_name} "
                f"(type: {url_info.content_type}, id: {url_info.post_id})"
            )

            # Уведомление о запросе в супергруппу
            await notification_manager.notify_download_request(
                user_id=user_id,
                username=username,
                platform=platform_name,
                url=url,
                content_type=url_info.content_type
            )

            try:
                # Загружаем медиа (используем url_info.url - может быть нормализован)
                download_result = await media_downloader.download(
                    url=url_info.url,
                    content_type=url_info.content_type,
                    platform=platform_name,
                )

                await process_download_result(
                    message, status_msg, download_result, url, url_info,
                    platform_emoji, platform_name, user_id, username, start_time,
                    daily_count=daily_count, is_premium=is_premium_user
                )

            except Exception as e:
                logger.error(f"Error in download process: {str(e)}")

                # Логируем исключение
                await sheets_manager.log_error(
                    user_id=user_id,
                    error_type="download_exception",
                    error_message=str(e),
                    url=url,
                    platform=platform_name
                )

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


async def handle_youtube_quality_selection(message: types.Message, url: str, platform_emoji: str, platform_name: str, user_id: int, username: str):
    """Показывает кнопки выбора качества для YouTube"""

    # Отправляем сообщение о получении информации
    status_msg = await message.answer(
        f"{platform_emoji} *{platform_name}*\n\n"
        f"⏳ Получаю информацию о видео...",
        parse_mode="Markdown"
    )

    try:
        # Получаем доступные форматы
        formats = await media_downloader.get_youtube_formats(url)

        if not formats:
            await status_msg.edit_text(
                f"❌ *Не удалось получить информацию о видео*\n\n"
                f"Возможно видео недоступно или приватное.",
                parse_mode="Markdown"
            )
            return

        # Формируем кнопки для доступных качеств
        buttons = []
        available_qualities = []

        for quality in [360, 480, 720, 1080]:
            if quality in formats:
                available_qualities.append(quality)
                size_mb = formats[quality].get("filesize", 0) / (1024 * 1024) if formats[quality].get("filesize") else 0
                size_text = f" ({size_mb:.1f} MB)" if size_mb > 0 else ""
                buttons.append([InlineKeyboardButton(
                    text=f"📥 Скачать в {quality}p{size_text}",
                    callback_data=f"yt_quality_{quality}"
                )])

        if not buttons:
            # Если нет стандартных форматов, добавляем 360p по умолчанию
            buttons.append([InlineKeyboardButton(
                text="📥 Скачать в 360p",
                callback_data="yt_quality_360"
            )])
            available_qualities.append(360)

        # Добавляем кнопку "Только звук" (доступна всем)
        buttons.append([InlineKeyboardButton(
            text="🎵 Только звук (MP3)",
            callback_data="yt_audio_only"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        # Формируем текст с информацией о видео
        title = formats.get("title", "Видео")
        duration = formats.get("duration", 0)
        duration_text = ""
        if duration:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            duration_text = f"\n⏱️ Длительность: {minutes}:{seconds:02d}"

        # Сохраняем данные в кэш
        msg = await status_msg.edit_text(
            f"{platform_emoji} *{platform_name}*\n\n"
            f"📹 {title[:100]}{'...' if len(title) > 100 else ''}{duration_text}\n\n"
            f"Выберите качество:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        # Сохраняем URL и форматы для callback
        youtube_urls_cache[msg.message_id] = url
        youtube_formats_cache[msg.message_id] = {
            "formats": available_qualities,
            "user_id": user_id,
            "username": username,
            "original_message_id": message.message_id
        }

        logger.info(f"User {user_id}: YouTube quality selection shown for {url}")

    except Exception as e:
        logger.error(f"Error showing YouTube quality selection: {e}")
        await status_msg.edit_text(
            f"❌ *Ошибка получения информации*\n\n{str(e)[:100]}",
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("yt_quality_"))
async def handle_youtube_quality_callback(callback: CallbackQuery):
    """Обрабатывает выбор качества YouTube"""
    try:
        quality = int(callback.data.replace("yt_quality_", ""))
        message_id = callback.message.message_id

        # Получаем URL и данные из кэша
        url = youtube_urls_cache.get(message_id)
        cache_data = youtube_formats_cache.get(message_id, {})

        if not url:
            await callback.answer("Ссылка не найдена, отправьте заново", show_alert=True)
            return

        user_id = cache_data.get("user_id", callback.from_user.id)
        username = cache_data.get("username", callback.from_user.username)

        # Проверяем Premium статус для HD качества
        is_premium = await sheets_manager.is_user_premium(user_id)

        # Если качество НЕ 360p и пользователь НЕ Premium - показываем PRO-экран
        if quality != 360 and not is_premium:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="yt_back"),
                    InlineKeyboardButton(text="⭐ Стать PRO", callback_data="show_premium"),
                ]
            ])

            await callback.message.edit_text(
                f"🔒 *Качество {quality}p*\n\n"
                f"Это качество доступно только для PRO-пользователей.\n\n"
                f"С PRO-подпиской вы сможете скачивать видео в HD качестве!",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            await callback.answer()
            return

        # 360p бесплатно или Premium пользователь - скачиваем
        await callback.answer("⏳ Начинаю загрузку...")

        await callback.message.edit_text(
            f"🎥 *YouTube*\n\n"
            f"⏳ Загрузка в {quality}p...\n"
            f"Пожалуйста, подождите.",
            parse_mode="Markdown",
            reply_markup=None
        )

        start_time = time.time()

        # Уведомление о запросе
        await notification_manager.notify_download_request(
            user_id=user_id,
            username=username,
            platform="YouTube",
            url=url,
            content_type=f"video_{quality}p"
        )

        # Скачиваем видео
        download_result = await media_downloader.download_youtube_quality(url, quality)

        if download_result.success and download_result.file_path:
            file_size_mb = download_result.file_size / (1024 * 1024)
            processing_time = time.time() - start_time

            # Логируем в Google Sheets
            await sheets_manager.log_request(
                user_id=user_id,
                username=username,
                platform="YouTube",
                content_type=f"video_{quality}p",
                url=url,
                success=True,
                file_size_mb=file_size_mb,
                duration_sec=download_result.duration or 0,
                processing_time=processing_time
            )

            # Уведомление об успехе
            await notification_manager.notify_download_success(
                user_id=user_id,
                username=username,
                platform="YouTube",
                file_size_mb=file_size_mb,
                duration=download_result.duration
            )

            # Формируем caption
            caption_parts = ["✅ YouTube", ""]

            if download_result.author:
                caption_parts.append(f"📝 {download_result.author}")

            stats = f"📊 {file_size_mb:.1f} MB"
            if download_result.duration:
                minutes = int(download_result.duration // 60)
                seconds = int(download_result.duration % 60)
                stats += f" ⏱️ {minutes}:{seconds:02d}"
            if download_result.views:
                views = download_result.views
                if views >= 1000000:
                    stats += f" 👁 {views/1000000:.1f}M"
                elif views >= 1000:
                    stats += f" 👁 {views/1000:.1f}K"
                else:
                    stats += f" 👁 {views}"
            if download_result.likes:
                likes = download_result.likes
                if likes >= 1000:
                    stats += f" ❤️ {likes/1000:.1f}K"
                else:
                    stats += f" ❤️ {likes}"
            caption_parts.append(stats)

            # Рекламная строка
            caption_parts.append("")
            caption_parts.append("🔻 Посты из соц.сетей в личку @UspSocDownloader\\_bot")

            caption = "\n".join(caption_parts)

            # Удаляем сообщение со статусом
            try:
                await callback.message.delete()
            except:
                pass

            # Отправляем видео
            await callback.message.answer_video(
                types.FSInputFile(download_result.file_path),
                caption=caption,
                parse_mode="Markdown"
            )

            # Удаляем оригинальное сообщение с URL
            try:
                original_msg_id = cache_data.get("original_message_id")
                if original_msg_id:
                    await callback.bot.delete_message(callback.message.chat.id, original_msg_id)
            except:
                pass

            logger.info(f"User {user_id}: YouTube {quality}p download successful")

        else:
            error_msg = download_result.error_message or "Неизвестная ошибка"

            await sheets_manager.log_request(
                user_id=user_id,
                username=username,
                platform="YouTube",
                content_type=f"video_{quality}p",
                url=url,
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )

            await notification_manager.notify_download_error(
                user_id=user_id,
                username=username,
                platform="YouTube",
                error=error_msg,
                url=url
            )

            await callback.message.edit_text(
                f"❌ *Не удалось загрузить*\n\n"
                f"Ошибка: {error_msg}",
                parse_mode="Markdown"
            )

        # Очищаем кэш
        youtube_urls_cache.pop(message_id, None)
        youtube_formats_cache.pop(message_id, None)

    except Exception as e:
        logger.error(f"Error in YouTube quality callback: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "yt_back")
async def handle_youtube_back_callback(callback: CallbackQuery):
    """Возврат к выбору качества YouTube"""
    try:
        message_id = callback.message.message_id
        cache_data = youtube_formats_cache.get(message_id, {})
        available_qualities = cache_data.get("formats", [360])

        # Восстанавливаем кнопки
        buttons = []
        for quality in available_qualities:
            buttons.append([InlineKeyboardButton(
                text=f"📥 Скачать в {quality}p",
                callback_data=f"yt_quality_{quality}"
            )])

        # Добавляем кнопку "Только звук"
        buttons.append([InlineKeyboardButton(
            text="🎵 Только звук (MP3)",
            callback_data="yt_audio_only"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            f"🎥 *YouTube*\n\n"
            f"Выберите качество:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in YouTube back callback: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "yt_audio_only")
async def handle_youtube_audio_callback(callback: CallbackQuery):
    """Скачивает только аудио с YouTube"""
    try:
        message_id = callback.message.message_id

        # Получаем URL и данные из кэша
        url = youtube_urls_cache.get(message_id)
        cache_data = youtube_formats_cache.get(message_id, {})

        if not url:
            await callback.answer("Ссылка не найдена, отправьте заново", show_alert=True)
            return

        user_id = cache_data.get("user_id", callback.from_user.id)
        username = cache_data.get("username", callback.from_user.username)

        await callback.answer("⏳ Начинаю загрузку аудио...")

        await callback.message.edit_text(
            f"🎵 *YouTube*\n\n"
            f"⏳ Загрузка аудио (MP3)...\n"
            f"Пожалуйста, подождите.",
            parse_mode="Markdown",
            reply_markup=None
        )

        start_time = time.time()

        # Уведомление о запросе
        await notification_manager.notify_download_request(
            user_id=user_id,
            username=username,
            platform="YouTube",
            url=url,
            content_type="audio"
        )

        # Скачиваем аудио
        download_result = await media_downloader.download_youtube_audio(url)

        if download_result.success and download_result.file_path:
            file_size_mb = download_result.file_size / (1024 * 1024)
            processing_time = time.time() - start_time

            # Логируем в Google Sheets
            await sheets_manager.log_request(
                user_id=user_id,
                username=username,
                platform="YouTube",
                content_type="audio",
                url=url,
                success=True,
                file_size_mb=file_size_mb,
                duration_sec=download_result.duration or 0,
                processing_time=processing_time
            )

            # Уведомление об успехе
            await notification_manager.notify_download_success(
                user_id=user_id,
                username=username,
                platform="YouTube",
                file_size_mb=file_size_mb,
                duration=download_result.duration
            )

            # Формируем caption
            caption_parts = ["✅ YouTube Audio", ""]

            if download_result.author:
                caption_parts.append(f"📝 {download_result.author}")

            stats = f"📊 {file_size_mb:.1f} MB"
            if download_result.duration:
                minutes = int(download_result.duration // 60)
                seconds = int(download_result.duration % 60)
                stats += f" ⏱️ {minutes}:{seconds:02d}"
            caption_parts.append(stats)

            # Рекламная строка
            caption_parts.append("")
            caption_parts.append("🔻 Посты из соц.сетей в личку @UspSocDownloader\\_bot")

            caption = "\n".join(caption_parts)

            # Удаляем сообщение со статусом
            try:
                await callback.message.delete()
            except:
                pass

            # Отправляем аудио
            await callback.message.answer_audio(
                types.FSInputFile(download_result.file_path),
                title=download_result.title or "YouTube Audio",
                performer=download_result.author,
                caption=caption,
                parse_mode="Markdown"
            )

            # Удаляем оригинальное сообщение с URL
            try:
                original_msg_id = cache_data.get("original_message_id")
                if original_msg_id:
                    await callback.bot.delete_message(callback.message.chat.id, original_msg_id)
            except:
                pass

            logger.info(f"User {user_id}: YouTube audio download successful")

        else:
            error_msg = download_result.error_message or "Неизвестная ошибка"

            await sheets_manager.log_request(
                user_id=user_id,
                username=username,
                platform="YouTube",
                content_type="audio",
                url=url,
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )

            await notification_manager.notify_download_error(
                user_id=user_id,
                username=username,
                platform="YouTube",
                error=error_msg,
                url=url
            )

            await callback.message.edit_text(
                f"❌ *Не удалось загрузить аудио*\n\n"
                f"Ошибка: {error_msg}",
                parse_mode="Markdown"
            )

        # Очищаем кэш
        youtube_urls_cache.pop(message_id, None)
        youtube_formats_cache.pop(message_id, None)

    except Exception as e:
        logger.error(f"Error in YouTube audio callback: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


async def process_download_result(message, status_msg, download_result, url, url_info,
                                   platform_emoji, platform_name, user_id, username, start_time,
                                   daily_count: int = 0, is_premium: bool = False):
    """Обрабатывает результат загрузки и отправляет файл"""

    # Обработка слишком большого файла
    if download_result.success and download_result.is_too_large:
        file_path = download_result.file_path
        file_size_mb = download_result.file_size / (1024 * 1024)

        try:
            await status_msg.delete()
        except:
            pass

        # Кэшируем путь для callback
        large_files_cache[message.message_id] = {
            "file_path": file_path,
            "platform": platform_name,
            "user_id": user_id,
            "username": username,
            "url": url,
            "download_result": download_result
        }

        if is_premium:
            # Premium - показываем кнопку отправки как файл
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📄 Отправить как файл", callback_data=f"send_as_file_{message.message_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_large_file")]
            ])
            await message.answer(
                f"⚠️ *Файл слишком большой*\n\n"
                f"Платформа: {platform_name}\n"
                f"Размер: {file_size_mb:.1f} MB (лимит 200 MB)\n\n"
                f"💎 Как Premium пользователь, вы можете получить файл без сжатия.",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            # Бесплатный пользователь - только предупреждение
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Получить Premium", callback_data="show_premium")]
            ])
            await message.answer(
                f"⚠️ *Файл слишком большой*\n\n"
                f"Платформа: {platform_name}\n"
                f"Размер: {file_size_mb:.1f} MB (лимит 200 MB)\n\n"
                f"💎 Premium пользователи могут скачивать большие файлы.",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        # Удаляем файл если не Premium
        if not is_premium and file_path:
            try:
                import os
                os.remove(file_path)
            except:
                pass

        return

    if download_result.success and download_result.file_path:
        file_path = download_result.file_path
        file_size_mb = download_result.file_size / (1024 * 1024)
        processing_time = time.time() - start_time

        logger.info(f"User {user_id}: Download successful ({file_size_mb:.1f} MB)")

        # Логируем в Google Sheets
        await sheets_manager.log_request(
            user_id=user_id,
            username=username,
            platform=platform_name,
            content_type=url_info.content_type,
            url=url,
            success=True,
            file_size_mb=file_size_mb,
            duration_sec=download_result.duration or 0,
            processing_time=processing_time
        )

        # Уведомление об успешном скачивании
        await notification_manager.notify_download_success(
            user_id=user_id,
            username=username,
            platform=platform_name,
            file_size_mb=file_size_mb,
            duration=download_result.duration
        )

        # Формируем caption в новом формате
        caption_parts = []

        # Заголовок: ✅ Instagram
        caption_parts.append(f"✅ {platform_name}")
        caption_parts.append("")

        # Автор со ссылкой
        author = download_result.author or ""
        post_url = download_result.url or url
        if author:
            caption_parts.append(f"📝 [{author}]({post_url})")

        # Статистика
        stats = f"📊 {file_size_mb:.1f} MB"
        if download_result.duration:
            minutes = int(download_result.duration // 60)
            seconds = int(download_result.duration % 60)
            stats += f" ⏱️ {minutes}:{seconds:02d}"
        if download_result.likes:
            likes = download_result.likes
            if likes >= 1000000:
                stats += f" ❤️ {likes/1000000:.1f}M"
            elif likes >= 1000:
                stats += f" ❤️ {likes/1000:.1f}K"
            else:
                stats += f" ❤️ {likes}"
        if download_result.comments:
            comments = download_result.comments
            if comments >= 1000:
                stats += f" 💬 {comments/1000:.1f}K"
            else:
                stats += f" 💬 {comments}"
        if download_result.views:
            views = download_result.views
            if views >= 1000000:
                stats += f" 👁 {views/1000000:.1f}M"
            elif views >= 1000:
                stats += f" 👁 {views/1000:.1f}K"
            else:
                stats += f" 👁 {views}"
        caption_parts.append(stats)

        # Рекламная строка
        caption_parts.append("")
        caption_parts.append("🔻 Посты из соц.сетей в личку @UspSocDownloader\\_bot")

        # Описание поста - отправляем отдельным сообщением
        description_text = download_result.description or ""
        extra_text = description_text if description_text else None

        caption = "\n".join(caption_parts)

        # Удаляем статус
        try:
            await status_msg.delete()
        except:
            pass

        # Отправляем файл(ы)
        try:
            # Проверяем - это карусель?
            if download_result.is_carousel and download_result.file_paths:
                media_group = []
                for i, fpath in enumerate(download_result.file_paths):
                    if fpath.endswith(('.mp4', '.mov', '.avi', '.webm')):
                        media_item = types.InputMediaVideo(
                            media=types.FSInputFile(fpath),
                            caption=caption if i == 0 else None,
                            parse_mode="Markdown" if i == 0 else None
                        )
                    else:
                        media_item = types.InputMediaPhoto(
                            media=types.FSInputFile(fpath),
                            caption=caption if i == 0 else None,
                            parse_mode="Markdown" if i == 0 else None
                        )
                    media_group.append(media_item)

                if len(media_group) > 10:
                    media_group = media_group[:10]

                await message.answer_media_group(media_group)

            elif url_info.content_type in ["video", "reel", "shorts", "clip"]:
                await message.answer_video(
                    types.FSInputFile(file_path),
                    caption=caption if caption else None,
                    parse_mode="Markdown"
                )
            elif url_info.content_type == "audio":
                await message.answer_audio(
                    types.FSInputFile(file_path),
                    title=download_result.title or "Audio",
                    caption=caption if caption else None,
                    parse_mode="Markdown"
                )
            elif url_info.content_type == "photo":
                await message.answer_photo(
                    types.FSInputFile(file_path),
                    caption=caption if caption else None,
                    parse_mode="Markdown"
                )
            else:
                await message.answer_document(
                    types.FSInputFile(file_path),
                    caption=caption if caption else None,
                    parse_mode="Markdown"
                )

            # Собираем пути к изображениям для OCR
            all_image_paths = []
            if download_result.is_carousel and download_result.file_paths:
                all_image_paths = [p for p in download_result.file_paths
                                 if p.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            elif file_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                all_image_paths = [file_path]

            # Проверяем, есть ли текст на изображениях
            has_image_text = False
            if all_image_paths:
                has_image_text = await check_images_have_text(all_image_paths)

            # Если есть текст поста - отправляем отдельным сообщением
            if extra_text:
                if len(extra_text) > 4000:
                    extra_text = extra_text[:4000] + "..."

                is_russian = is_russian_text(extra_text)

                buttons = []
                if not is_russian:
                    buttons.append([InlineKeyboardButton(
                        text="🌐 Перевести на русский",
                        callback_data="translate"
                    )])
                else:
                    buttons.append([InlineKeyboardButton(
                        text="✍️ Сделать рерайт",
                        callback_data="rewrite_menu"
                    )])

                if has_image_text:
                    buttons.append([InlineKeyboardButton(
                        text="📷 Получить текст с картинок",
                        callback_data="ocr_extract"
                    )])

                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                sent_msg = await message.answer(extra_text, reply_markup=keyboard)

                original_texts_cache[sent_msg.message_id] = extra_text
                if has_image_text:
                    image_paths_cache[sent_msg.message_id] = all_image_paths

            elif has_image_text:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📷 Получить текст с картинок",
                        callback_data="ocr_extract"
                    )]
                ])
                sent_msg = await message.answer(
                    "📷 На изображениях обнаружен текст",
                    reply_markup=keyboard
                )
                image_paths_cache[sent_msg.message_id] = all_image_paths

            # Удаляем исходное сообщение с ссылкой
            try:
                await message.delete()
            except Exception as e:
                logger.warning(f"Could not delete original message: {e}")

            logger.info(f"User {message.from_user.id}: File sent successfully")

            # Уведомление о приближении к лимиту (для бесплатных пользователей)
            if not is_premium and daily_count > 0:
                remaining = FREE_DAILY_LIMIT - daily_count - 1  # -1 за текущее скачивание
                if remaining <= 2 and remaining >= 0:
                    # Показываем уведомление + кнопку "Поделиться"
                    share_text = "Качай видео с Instagram, TikTok, YouTube без рекламы!"

                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="📤 Поделиться ботом",
                            switch_inline_query=share_text
                        )],
                        [InlineKeyboardButton(text="💎 Получить Premium", callback_data="show_premium")]
                    ])

                    if remaining == 0:
                        limit_text = (
                            f"⚠️ <b>Это было последнее бесплатное скачивание сегодня!</b>\n\n"
                            f"Лимит обновится в полночь.\n"
                            f"💎 Получите Premium для безлимитных скачиваний."
                        )
                    else:
                        limit_text = (
                            f"💡 <b>Осталось {remaining} бесплатных скачивани{'е' if remaining == 1 else 'я'} сегодня</b>\n\n"
                            f"💎 Получите Premium для безлимитных скачиваний.\n"
                            f"📤 Или поделитесь ботом с друзьями!"
                        )

                    await message.answer(limit_text, parse_mode="HTML", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            await message.answer(
                f"⚠️ Файл загружен, но не удалось отправить\n"
                f"Ошибка: {str(e)[:100]}"
            )

    else:
        # Ошибка загрузки
        error_msg = download_result.error_message or "Неизвестная ошибка"
        processing_time = time.time() - start_time
        logger.warning(f"User {user_id}: Download failed - {error_msg}")

        await sheets_manager.log_request(
            user_id=user_id,
            username=username,
            platform=platform_name,
            content_type=url_info.content_type,
            url=url,
            success=False,
            error_message=error_msg,
            processing_time=processing_time
        )

        await notification_manager.notify_download_error(
            user_id=user_id,
            username=username,
            platform=platform_name,
            error=error_msg,
            url=url
        )

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


@router.callback_query(F.data == "translate")
async def handle_translate_callback(callback: CallbackQuery):
    """Обрабатывает нажатие кнопки перевода"""
    try:
        message_id = callback.message.message_id
        original_text = original_texts_cache.get(message_id)

        if not original_text:
            original_text = callback.message.text

        if not original_text:
            await callback.answer("Текст не найден", show_alert=True)
            return

        await callback.answer()

        is_html_content = "<pre>" in original_text or "<b>" in original_text

        await callback.message.edit_text(
            "⏳ Выполняется перевод...",
            reply_markup=None
        )

        translated_text = await translate_to_russian(original_text)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✍️ Сделать рерайт",
                callback_data="rewrite_menu"
            )]
        ])

        await callback.message.edit_text(
            translated_text,
            reply_markup=keyboard,
            parse_mode="HTML" if is_html_content else None
        )

        original_texts_cache[message_id] = translated_text

        logger.info(f"Translated message {message_id} for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error in translate callback: {e}")
        await callback.answer(f"Ошибка перевода: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "rewrite_menu")
async def handle_rewrite_menu_callback(callback: CallbackQuery):
    """Показывает меню выбора стиля рерайта"""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎓 Экспертный", callback_data="rewrite_expert"),
                InlineKeyboardButton(text="😄 Юмористический", callback_data="rewrite_humor"),
            ],
            [
                InlineKeyboardButton(text="🤗 Дружелюбный", callback_data="rewrite_friendly"),
                InlineKeyboardButton(text="✨ Мой стиль", callback_data="rewrite_mystyle"),
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="rewrite_back"),
            ]
        ])

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in rewrite menu callback: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "rewrite_mystyle")
async def handle_rewrite_mystyle_callback(callback: CallbackQuery):
    """Показывает сообщение о PRO-аккаунте"""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="rewrite_menu"),
                InlineKeyboardButton(text="⭐ Стать PRO", callback_data="become_pro"),
            ]
        ])

        await callback.message.edit_text(
            "🔒 *Мой стиль*\n\n"
            "Эта функция доступна только на PRO-аккаунте.\n\n"
            "С PRO вы сможете создать свой уникальный стиль рерайта!",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in mystyle callback: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "become_pro")
async def handle_become_pro_callback(callback: CallbackQuery):
    """Обрабатывает нажатие кнопки Стать PRO"""
    try:
        await callback.answer("PRO-подписка скоро будет доступна! 🚀", show_alert=True)

    except Exception as e:
        logger.error(f"Error in become_pro callback: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "rewrite_back")
async def handle_rewrite_back_callback(callback: CallbackQuery):
    """Возврат к кнопке рерайта"""
    try:
        message_id = callback.message.message_id
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✍️ Сделать рерайт",
                callback_data="rewrite_menu"
            )]
        ])

        original_text = original_texts_cache.get(message_id)
        if original_text and callback.message.text != original_text:
            await callback.message.edit_text(original_text, reply_markup=keyboard)
        else:
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in rewrite back callback: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data.startswith("rewrite_"))
async def handle_rewrite_style_callback(callback: CallbackQuery):
    """Обрабатывает выбор стиля рерайта"""
    try:
        style = callback.data.replace("rewrite_", "")

        if style in ["menu", "back", "mystyle"]:
            return

        message_id = callback.message.message_id
        text_to_rewrite = original_texts_cache.get(message_id)

        if not text_to_rewrite:
            text_to_rewrite = callback.message.text

        if not text_to_rewrite:
            await callback.answer("Текст не найден", show_alert=True)
            return

        style_names = {
            "expert": "экспертном",
            "humor": "юмористическом",
            "friendly": "дружелюбном"
        }
        style_name = style_names.get(style, style)

        await callback.answer("⏳ Выполняется рерайт...")

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except:
            pass

        rewritten_text = await rewrite_text(text_to_rewrite, style)

        is_html_content = "<pre>" in text_to_rewrite or "<b>" in text_to_rewrite

        if is_html_content:
            await callback.message.reply(
                f"✍️ <b>Рерайт ({style_name} стиль):</b>\n\n{rewritten_text}",
                parse_mode="HTML"
            )
        else:
            await callback.message.reply(
                f"✍️ *Рерайт ({style_name} стиль):*\n\n{rewritten_text}",
                parse_mode="Markdown"
            )

        logger.info(f"Rewritten message {message_id} in {style} style for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error in rewrite style callback: {e}")
        await callback.answer(f"Ошибка рерайта: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "ocr_extract")
async def handle_ocr_extract_callback(callback: CallbackQuery):
    """Извлекает текст с изображений"""
    try:
        message_id = callback.message.message_id
        image_paths = image_paths_cache.get(message_id)

        if not image_paths:
            await callback.answer("Изображения не найдены", show_alert=True)
            return

        await callback.answer()

        original_text = callback.message.text
        original_markup = callback.message.reply_markup

        loading_text = original_text + "\n\n⏳ Получаю текст с картинок..."
        if original_markup:
            new_buttons = [row for row in original_markup.inline_keyboard
                         if not any(btn.callback_data == "ocr_extract" for btn in row)]
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=new_buttons) if new_buttons else None
        else:
            new_keyboard = None

        await callback.message.edit_text(loading_text, reply_markup=new_keyboard)

        extracted_text = await extract_text_from_images(image_paths)

        await callback.message.edit_text(original_text, reply_markup=new_keyboard)

        is_russian = is_russian_text(extracted_text)

        if not is_russian:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🌐 Перевести на русский",
                    callback_data="translate"
                )]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✍️ Сделать рерайт",
                    callback_data="rewrite_menu"
                )]
            ])

        if len(extracted_text) > 4000:
            extracted_text = extracted_text[:4000] + "..."

        sent_msg = await callback.message.reply(
            f"📷 <b>Текст с изображений:</b>\n\n{extracted_text}",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        original_texts_cache[sent_msg.message_id] = extracted_text

        logger.info(f"OCR extracted {len(extracted_text)} chars for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error in OCR callback: {e}")
        await callback.answer(f"Ошибка OCR: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data.startswith("send_as_file_"))
async def handle_send_as_file_callback(callback: CallbackQuery):
    """Отправляет большой файл как документ (только для Premium)"""
    try:
        message_id = int(callback.data.replace("send_as_file_", ""))
        cache_data = large_files_cache.get(message_id)

        if not cache_data:
            await callback.answer("Файл не найден. Попробуйте скачать заново.", show_alert=True)
            return

        file_path = cache_data.get("file_path")
        platform = cache_data.get("platform")
        download_result = cache_data.get("download_result")

        if not file_path:
            await callback.answer("Файл не найден", show_alert=True)
            return

        import os
        if not os.path.exists(file_path):
            await callback.answer("Файл был удалён. Скачайте заново.", show_alert=True)
            return

        await callback.answer("📤 Отправка файла...")

        await callback.message.edit_text(
            f"📤 *Отправка файла...*\n\n"
            f"Это может занять некоторое время для больших файлов.",
            parse_mode="Markdown",
            reply_markup=None
        )

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        # Формируем caption
        caption_parts = [f"✅ {platform}", ""]
        if download_result and download_result.author:
            caption_parts.append(f"📝 {download_result.author}")
        caption_parts.append(f"📊 {file_size_mb:.1f} MB")
        if download_result and download_result.duration:
            minutes = int(download_result.duration // 60)
            seconds = int(download_result.duration % 60)
            caption_parts.append(f"⏱️ {minutes}:{seconds:02d}")
        caption_parts.append("")
        caption_parts.append("🔻 Посты из соц.сетей в личку @UspSocDownloader\\_bot")
        caption = "\n".join(caption_parts)

        # Отправляем как документ
        await callback.message.answer_document(
            types.FSInputFile(file_path),
            caption=caption,
            parse_mode="Markdown"
        )

        # Удаляем сообщение с предупреждением
        try:
            await callback.message.delete()
        except:
            pass

        # Удаляем файл
        try:
            os.remove(file_path)
        except:
            pass

        # Удаляем из кэша
        large_files_cache.pop(message_id, None)

        logger.info(f"User {callback.from_user.id}: Large file sent as document ({file_size_mb:.1f} MB)")

    except Exception as e:
        logger.error(f"Error sending large file: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "cancel_large_file")
async def handle_cancel_large_file_callback(callback: CallbackQuery):
    """Отменяет отправку большого файла"""
    try:
        await callback.answer("Отменено")

        await callback.message.edit_text(
            "❌ Отправка отменена.\n\n"
            "Файл был удалён.",
            reply_markup=None
        )

        # Удаляем файлы из кэша
        for msg_id, data in list(large_files_cache.items()):
            if data.get("user_id") == callback.from_user.id:
                file_path = data.get("file_path")
                if file_path:
                    try:
                        import os
                        os.remove(file_path)
                    except:
                        pass
                large_files_cache.pop(msg_id, None)

    except Exception as e:
        logger.error(f"Error canceling large file: {e}")
