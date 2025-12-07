"""
Handler для обработки сообщений с URL и загрузки медиа
"""
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

logger = get_logger(__name__)
router = Router()

url_processor = URLProcessor()
media_downloader = MediaDownloader()

# Хранилище оригинальных текстов для перевода (message_id -> text)
original_texts = {}

# Хранилище путей к изображениям для OCR (message_id -> list of paths)
image_paths_cache = {}


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
                    file_size_mb = download_result.file_size / (1024 * 1024)

                    logger.info(
                        f"User {message.from_user.id}: Download successful ({file_size_mb:.1f} MB)"
                    )

                    # Формируем caption в новом формате
                    caption_parts = []

                    # Заголовок: ✅ Instagram
                    caption_parts.append(f"✅ {platform_name}")
                    caption_parts.append("")

                    # Автор со ссылкой: 📝 username (кликабельная ссылка)
                    author = download_result.author or ""
                    post_url = download_result.url or url
                    if author:
                        # Markdown ссылка: [username](url)
                        caption_parts.append(f"📝 [{author}]({post_url})")

                    # Статистика: 📊 19.7 MB ⏱️ 1:13 ❤️ 46K 💬 1K
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

                    # Описание поста - всегда отправляем отдельным сообщением с кнопками
                    description_text = download_result.description or ""
                    extra_text = description_text if description_text else None

                    # Caption без описания (описание идёт отдельно с кнопками)
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
                            # Отправляем медиа-группу
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

                            # Telegram позволяет до 10 медиа в группе
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
                            # Telegram message limit is 4096 chars
                            if len(extra_text) > 4000:
                                extra_text = extra_text[:4000] + "..."

                            # Проверяем язык текста
                            is_russian = is_russian_text(extra_text)

                            # Формируем кнопки
                            buttons = []

                            # Кнопка перевода или рерайта
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

                            # Кнопка OCR если есть текст на изображениях
                            if has_image_text:
                                buttons.append([InlineKeyboardButton(
                                    text="📷 Получить текст с картинок",
                                    callback_data="ocr_extract"
                                )])

                            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                            sent_msg = await message.answer(extra_text, reply_markup=keyboard)

                            # Сохраняем текст и пути к изображениям
                            original_texts[sent_msg.message_id] = extra_text
                            if has_image_text:
                                image_paths_cache[sent_msg.message_id] = all_image_paths

                        # Если нет текста поста, но есть текст на изображениях - показываем только кнопку OCR
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


@router.callback_query(F.data == "translate")
async def handle_translate_callback(callback: CallbackQuery):
    """Обрабатывает нажатие кнопки перевода"""
    try:
        message_id = callback.message.message_id

        # Получаем оригинальный текст
        original_text = original_texts.get(message_id)

        if not original_text:
            # Если текст не найден в кэше, берём текст сообщения
            original_text = callback.message.text

        if not original_text:
            await callback.answer("Текст не найден", show_alert=True)
            return

        await callback.answer()

        # Определяем, содержит ли текст HTML-теги (OCR результат)
        is_html_content = "<pre>" in original_text or "<b>" in original_text

        # Показываем индикатор загрузки
        await callback.message.edit_text(
            "⏳ Выполняется перевод...",
            reply_markup=None
        )

        # Переводим текст
        translated_text = await translate_to_russian(original_text)

        # После перевода показываем кнопку рерайта
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✍️ Сделать рерайт",
                callback_data="rewrite_menu"
            )]
        ])

        # Редактируем сообщение с переведённым текстом
        # Используем HTML если оригинал был HTML
        await callback.message.edit_text(
            translated_text,
            reply_markup=keyboard,
            parse_mode="HTML" if is_html_content else None
        )

        # Обновляем кэш с переведённым текстом для рерайта
        original_texts[message_id] = translated_text

        logger.info(f"Translated message {message_id} for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error in translate callback: {e}")
        await callback.answer(f"Ошибка перевода: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "rewrite_menu")
async def handle_rewrite_menu_callback(callback: CallbackQuery):
    """Показывает меню выбора стиля рерайта"""
    try:
        # Показываем кнопки выбора стиля
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

        # Если текст изменился (показывали PRO-экран), восстанавливаем оригинал
        original_text = original_texts.get(message_id)
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

        # Пропускаем служебные callback
        if style in ["menu", "back", "mystyle"]:
            return

        message_id = callback.message.message_id

        # Получаем текст для рерайта
        text_to_rewrite = original_texts.get(message_id)

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

        # Убираем кнопки стилей с оригинального сообщения
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except:
            pass

        # Делаем рерайт
        rewritten_text = await rewrite_text(text_to_rewrite, style)

        # Определяем, содержит ли текст HTML-теги (OCR результат)
        is_html_content = "<pre>" in text_to_rewrite or "<b>" in text_to_rewrite

        # Отправляем рерайт как reply на оригинальное сообщение
        if is_html_content:
            # HTML формат для OCR текста
            await callback.message.reply(
                f"✍️ <b>Рерайт ({style_name} стиль):</b>\n\n{rewritten_text}",
                parse_mode="HTML"
            )
        else:
            # Markdown для обычного текста
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

        # Получаем пути к изображениям
        image_paths = image_paths_cache.get(message_id)

        if not image_paths:
            await callback.answer("Изображения не найдены", show_alert=True)
            return

        await callback.answer()

        # Сохраняем оригинальный текст и показываем индикатор загрузки
        original_text = callback.message.text
        original_markup = callback.message.reply_markup

        # Убираем кнопку OCR и показываем статус загрузки
        loading_text = original_text + "\n\n⏳ Получаю текст с картинок..."
        # Убираем кнопку OCR из клавиатуры
        if original_markup:
            new_buttons = [row for row in original_markup.inline_keyboard
                         if not any(btn.callback_data == "ocr_extract" for btn in row)]
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=new_buttons) if new_buttons else None
        else:
            new_keyboard = None

        await callback.message.edit_text(loading_text, reply_markup=new_keyboard)

        # Извлекаем текст
        extracted_text = await extract_text_from_images(image_paths)

        # Убираем кнопку OCR навсегда (оставляем только другие кнопки)
        await callback.message.edit_text(original_text, reply_markup=new_keyboard)

        # Проверяем язык извлечённого текста
        is_russian = is_russian_text(extracted_text)

        # Формируем кнопки для извлечённого текста
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

        # Ограничиваем длину текста
        if len(extracted_text) > 4000:
            extracted_text = extracted_text[:4000] + "..."

        # Отправляем извлечённый текст как reply (HTML для корректного <pre>)
        sent_msg = await callback.message.reply(
            f"📷 <b>Текст с изображений:</b>\n\n{extracted_text}",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        # Сохраняем текст для возможного перевода/рерайта
        original_texts[sent_msg.message_id] = extracted_text

        logger.info(f"OCR extracted {len(extracted_text)} chars for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error in OCR callback: {e}")
        await callback.answer(f"Ошибка OCR: {str(e)[:50]}", show_alert=True)
