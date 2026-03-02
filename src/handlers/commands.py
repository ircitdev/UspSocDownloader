"""Handler for user and admin commands."""
import os
from datetime import datetime
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from src.utils.logger import get_logger
from src.utils.sheets import sheets_manager
from src.utils.text_helpers import safe_format_error
from src.config import config
from src.database.db_manager import get_db_manager

logger = get_logger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id == config.ADMIN_ID


# ==================== ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ====================

@router.message(Command("stats"))
async def stats_command(message: types.Message) -> None:
    """Показать статистику пользователя."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested stats")

    try:
        user_stats = await sheets_manager.get_user_stats(user_id)

        if user_stats:
            text = (
                "📊 <b>Ваша статистика</b>\n\n"
                f"🆔 ID: <code>{user_stats.get('user_id', user_id)}</code>\n"
                f"📅 Первый визит: {user_stats.get('first_seen', 'н/д')}\n"
                f"🕐 Последний визит: {user_stats.get('last_seen', 'н/д')}\n"
                f"📥 Всего запросов: {user_stats.get('total_requests', 0)}\n"
                f"📊 Статус: {user_stats.get('status', 'active')}\n"
            )
        else:
            text = (
                "📊 <b>Ваша статистика</b>\n\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                "📥 Запросов: 0\n\n"
                "💡 Отправьте ссылку на видео, чтобы начать!"
            )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error getting stats for {user_id}: {e}")
        await message.answer("❌ Не удалось получить статистику. Попробуйте позже.")


@router.message(Command("ref"))
async def ref_command(message: types.Message) -> None:
    """Показать реферальную ссылку."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested referral link")

    bot_username = (await message.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    text = (
        "🔗 <b>Ваша реферальная ссылка</b>\n\n"
        f"<code>{ref_link}</code>\n\n"
        "📤 Поделитесь ссылкой с друзьями!\n"
        "Когда они зарегистрируются, вы получите бонусы.\n\n"
        "💡 Нажмите на ссылку, чтобы скопировать."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться", switch_inline_query=ref_link)]
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.message(Command("premium"))
async def premium_command(message: types.Message) -> None:
    """Показать тарифы и способы оплаты Premium."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested premium info")

    # Проверяем текущий статус пользователя
    is_premium = await sheets_manager.is_user_premium(user_id)

    if is_premium:
        text = (
            "⭐ <b>У вас уже есть Premium!</b>\n\n"
            "Вам доступны все функции:\n"
            "✅ Безлимитные скачивания\n"
            "✅ HD качество (720p, 1080p)\n"
            "✅ Приоритетная очередь\n"
            "✅ Без рекламы\n\n"
            "💎 Спасибо, что вы с нами!"
        )
        await message.answer(text, parse_mode="HTML")
        return

    # Получаем количество скачиваний сегодня
    daily_count = await sheets_manager.get_user_daily_requests(user_id)

    text = (
        "💎 <b>Premium подписка</b>\n\n"
        f"📊 Сегодня использовано: {daily_count}/10 бесплатных скачиваний\n\n"
        "<b>Преимущества Premium:</b>\n"
        "✅ Безлимитные скачивания (без лимита 10/день)\n"
        "✅ HD качество YouTube (720p, 1080p)\n"
        "✅ Приоритетная очередь\n"
        "✅ Уникальные стили рерайта\n"
        "✅ Без рекламы\n\n"
        "<b>Тарифы:</b>\n"
        "📅 1 месяц — <b>199 ₽</b>\n"
        "📅 3 месяца — <b>499 ₽</b> <s>597 ₽</s>\n"
        "📅 1 год — <b>1499 ₽</b> <s>2388 ₽</s>\n\n"
        "💳 <b>Способы оплаты:</b>\n"
        "• Банковская карта (Visa/MasterCard/МИР)\n"
        "• СБП (Система быстрых платежей)\n"
        "• ЮMoney\n\n"
        "📩 Для оплаты напишите админу: @smit_support"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 1 месяц — 199 ₽", callback_data="pay_1month")],
        [InlineKeyboardButton(text="💳 Оплатить 3 месяца — 499 ₽", callback_data="pay_3month")],
        [InlineKeyboardButton(text="💳 Оплатить 1 год — 1499 ₽", callback_data="pay_1year")],
        [InlineKeyboardButton(text="📩 Написать в поддержку", url="https://t.me/smit_support")]
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.message(Command("platforms"))
async def platforms_command(message: types.Message) -> None:
    """Показать список поддерживаемых платформ."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested platforms list")

    text = (
        "🌐 <b>Поддерживаемые платформы</b>\n\n"
        "📸 <b>Instagram</b>\n"
        "   • Фото и видео из постов\n"
        "   • Reels\n"
        "   • Карусели (несколько фото/видео)\n\n"
        "🎵 <b>TikTok</b>\n"
        "   • Видео без водяного знака\n\n"
        "🎥 <b>YouTube</b>\n"
        "   • Видео (360p бесплатно, HD для Premium)\n"
        "   • Shorts\n"
        "   • Аудио (MP3)\n\n"
        "🐦 <b>Twitter / X</b>\n"
        "   • Видео из твитов\n"
        "   • Фото\n"
        "   • GIF\n\n"
        "📘 <b>Facebook</b>\n"
        "   • Публичные видео\n"
        "   • Reels\n\n"
        "💡 <b>Как пользоваться:</b>\n"
        "Просто отправьте ссылку на пост — бот всё скачает автоматически!"
    )

    await message.answer(text, parse_mode="HTML")


@router.message(Command("history"))
async def history_command(message: types.Message) -> None:
    """Показать историю загрузок пользователя."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested download history")

    try:
        db = get_db_manager()
        if not db:
            await message.answer("⚠️ История временно недоступна")
            return

        # Получаем последние 10 загрузок
        history = await db.get_download_history(user_id, limit=10)

        if not history:
            text = (
                "📂 <b>История загрузок</b>\n\n"
                "История пуста. Скачайте что-нибудь!\n\n"
                "💡 Просто отправьте ссылку на пост из Instagram, YouTube, TikTok или VK"
            )
            await message.answer(text, parse_mode="HTML")
            return

        # Эмодзи для платформ
        platform_emoji = {
            "Instagram": "📸",
            "YouTube": "📺",
            "TikTok": "🎵",
            "VK": "🎬",
            "Twitter": "🐦",
            "X": "🐦"
        }

        # Формируем текст с историей
        items = []
        buttons = []

        for i, item in enumerate(history[:10], 1):
            emoji = platform_emoji.get(item['platform'], "📁")

            # Дата в читаемом формате
            try:
                date = datetime.fromisoformat(item['download_date'])
                date_str = date.strftime("%d.%m %H:%M")
            except:
                date_str = "недавно"

            # Сокращаем название до 35 символов
            title = (item['title'] or "Без названия")[:35]
            if len(item['title'] or "") > 35:
                title += "..."

            # Размер файла
            file_size = item['file_size'] or 0
            size_mb = file_size / 1024 / 1024 if file_size > 0 else 0

            # Формат строки
            favorite_mark = "⭐ " if item['is_favorite'] else ""
            items.append(
                f"{i}. {emoji} {favorite_mark}<b>{title}</b>\n"
                f"   {date_str} • {size_mb:.1f} MB"
            )

            # Кнопки для первых 5 элементов
            if i <= 5:
                row = []
                row.append(InlineKeyboardButton(
                    text=f"{i}. Скачать снова",
                    callback_data=f"history_redownload_{item['id']}"
                ))

                # Кнопка избранного (добавить или удалить)
                if item['is_favorite']:
                    row.append(InlineKeyboardButton(
                        text="💔",
                        callback_data=f"history_unfavorite_{item['id']}"
                    ))
                else:
                    row.append(InlineKeyboardButton(
                        text="⭐",
                        callback_data=f"history_favorite_{item['id']}"
                    ))

                buttons.append(row)

        text = (
            "📂 <b>История загрузок</b>\n\n" +
            "\n\n".join(items)
        )

        # Добавляем кнопку "Показать больше" если есть больше 10 записей
        total_count = len(history)
        if total_count >= 10:
            buttons.append([InlineKeyboardButton(
                text="📊 Показать больше",
                callback_data="history_show_more_10"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in history command: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


@router.message(Command("favorites"))
async def favorites_command(message: types.Message) -> None:
    """Показать избранные загрузки."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested favorites")

    try:
        db = get_db_manager()
        if not db:
            await message.answer("⚠️ Избранное временно недоступно")
            return

        # Получаем избранные загрузки
        favorites = await db.get_download_history(user_id, limit=50, favorites_only=True)

        if not favorites:
            text = (
                "⭐ <b>Избранное</b>\n\n"
                "Избранное пусто.\n\n"
                "💡 Добавляйте загрузки в избранное через /history или нажимая ⭐ при просмотре"
            )
            await message.answer(text, parse_mode="HTML")
            return

        # Эмодзи для платформ
        platform_emoji = {
            "Instagram": "📸",
            "YouTube": "📺",
            "TikTok": "🎵",
            "VK": "🎬",
            "Twitter": "🐦",
            "X": "🐦"
        }

        # Формируем текст с избранным
        items = []
        buttons = []

        for i, item in enumerate(favorites[:10], 1):
            emoji = platform_emoji.get(item['platform'], "📁")

            # Дата
            try:
                date = datetime.fromisoformat(item['download_date'])
                date_str = date.strftime("%d.%m %H:%M")
            except:
                date_str = "недавно"

            # Название
            title = (item['title'] or "Без названия")[:35]
            if len(item['title'] or "") > 35:
                title += "..."

            # Размер
            file_size = item['file_size'] or 0
            size_mb = file_size / 1024 / 1024 if file_size > 0 else 0

            items.append(
                f"{i}. {emoji} <b>{title}</b>\n"
                f"   {date_str} • {size_mb:.1f} MB"
            )

            # Кнопки для первых 5 элементов
            if i <= 5:
                row = []
                row.append(InlineKeyboardButton(
                    text=f"{i}. Скачать",
                    callback_data=f"fav_download_{item['id']}"
                ))
                row.append(InlineKeyboardButton(
                    text="💔",
                    callback_data=f"fav_remove_{item['id']}"
                ))
                buttons.append(row)

        text = (
            f"⭐ <b>Избранное ({len(favorites)})</b>\n\n" +
            "\n\n".join(items)
        )

        # Кнопка показать больше
        if len(favorites) > 10:
            buttons.append([InlineKeyboardButton(
                text="📊 Показать все",
                callback_data="favorites_show_all"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in favorites command: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


@router.message(Command("settings"))
async def settings_command(message: types.Message) -> None:
    """Показать настройки пользователя."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} opened settings")

    try:
        db = get_db_manager()
        if not db:
            await message.answer("⚠️ Настройки временно недоступны")
            return

        settings = await db.get_user_settings(user_id)

        # Создаем inline keyboard с настройками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎬 Качество: {settings['default_quality']}",
                    callback_data="settings_quality"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📁 Формат: {settings['default_format'].upper()}",
                    callback_data="settings_format"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🗑️ Авто-удаление: {settings['auto_delete_after_days']} дн.",
                    callback_data="settings_autodelete"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔔 Уведомления: {'✅' if settings['notifications_enabled'] else '❌'}",
                    callback_data="settings_notifications"
                )
            ]
        ])

        text = (
            "⚙️ <b>Настройки</b>\n\n"
            f"🎬 <b>Качество по умолчанию:</b> {settings['default_quality']}\n"
            f"📁 <b>Формат:</b> {settings['default_format'].upper()}\n"
            f"🗑️ <b>Авто-удаление файлов:</b> через {settings['auto_delete_after_days']} дней\n"
            f"🔔 <b>Уведомления:</b> {'включены' if settings['notifications_enabled'] else 'выключены'}\n\n"
            "💡 Нажмите на параметр для изменения"
        )

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in settings command: {e}")
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


# ==================== АДМИНСКИЕ КОМАНДЫ ====================

@router.message(Command("admin"))
async def admin_command(message: types.Message) -> None:
    """Админ-панель."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} called /admin command (admin ID: {config.ADMIN_ID})")

    if not is_admin(user_id):
        logger.warning(f"User {user_id} attempted to access admin panel (not authorized)")
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    logger.info(f"Admin {user_id} opened admin panel")

    text = (
        "👑 <b>Админ-панель</b>\n\n"
        "<b>Доступные команды:</b>\n\n"
        "/allstats - 📈 Общая статистика бота\n"
        "/users - 👥 Список пользователей\n"
        "/broadcast &lt;текст&gt; - 📢 Рассылка всем\n"
        "/checkinstagram - 🔍 Проверить Instagram\n"
        "/setcookies - 🍪 Обновить cookies\n\n"
        "<b>Ссылки:</b>\n"
        "📊 <a href='https://docs.google.com/spreadsheets/d/1cQhOc-FyY5uF7cLC2nH0jht2pITrt0bc3swhvfhVUoI/'>Google Sheets</a>\n"
        "💬 <a href='https://t.me/c/3307715316/'>Супергруппа уведомлений</a>"
    )

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("allstats"))
async def allstats_command(message: types.Message) -> None:
    """Общая статистика бота (только для админа)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    logger.info(f"Admin {message.from_user.id} requested all stats")

    try:
        # Получаем данные из Google Sheets
        if not await sheets_manager.init():
            await message.answer("❌ Google Sheets недоступен.")
            return

        import asyncio
        loop = asyncio.get_event_loop()

        def get_stats():
            ws_users = sheets_manager.spreadsheet.worksheet("Users")
            ws_requests = sheets_manager.spreadsheet.worksheet("Requests")

            users = ws_users.get_all_values()[1:]  # Skip header
            requests = ws_requests.get_all_values()[1:]  # Skip header

            total_users = len(users)
            premium_users = sum(1 for u in users if len(u) > 10 and u[10] == "yes")

            total_requests = len(requests)
            successful = sum(1 for r in requests if len(r) > 6 and r[6] == "yes")

            # Platform stats
            platforms = {}
            for r in requests:
                if len(r) > 3 and r[3]:
                    p = r[3].lower()
                    platforms[p] = platforms.get(p, 0) + 1

            return {
                "total_users": total_users,
                "premium_users": premium_users,
                "total_requests": total_requests,
                "successful": successful,
                "platforms": platforms
            }

        stats = await loop.run_in_executor(None, get_stats)

        success_rate = (stats["successful"] / stats["total_requests"] * 100) if stats["total_requests"] > 0 else 0

        # Format platforms
        platform_text = "\n".join([
            f"  • {p}: {c}" for p, c in sorted(stats["platforms"].items(), key=lambda x: -x[1])
        ]) or "  Нет данных"

        text = (
            "📈 <b>Общая статистика</b>\n\n"
            f"👥 <b>Пользователи:</b> {stats['total_users']}\n"
            f"  ⭐ Premium: {stats['premium_users']}\n\n"
            f"📥 <b>Запросы:</b> {stats['total_requests']}\n"
            f"  ✅ Успешных: {stats['successful']} ({success_rate:.1f}%)\n"
            f"  ❌ Ошибок: {stats['total_requests'] - stats['successful']}\n\n"
            f"📊 <b>По платформам:</b>\n{platform_text}"
        )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error getting all stats: {e}")
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


@router.message(Command("users"))
async def users_command(message: types.Message) -> None:
    """Список последних пользователей (только для админа)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    logger.info(f"Admin {message.from_user.id} requested users list")

    try:
        if not await sheets_manager.init():
            await message.answer("❌ Google Sheets недоступен.")
            return

        import asyncio
        loop = asyncio.get_event_loop()

        def get_users():
            ws = sheets_manager.spreadsheet.worksheet("Users")
            users = ws.get_all_values()[1:]  # Skip header
            # Last 20 users, sorted by registration date (newest first)
            return users[-20:][::-1] if len(users) > 20 else users[::-1]

        users = await loop.run_in_executor(None, get_users)

        if not users:
            await message.answer("👥 Пользователей пока нет.")
            return

        text = "👥 <b>Последние пользователи:</b>\n\n"

        for u in users[:10]:  # Show max 10
            user_id = u[0] if len(u) > 0 else "?"
            username = u[1] if len(u) > 1 and u[1] else "нет"
            first_name = u[2] if len(u) > 2 else ""
            first_seen = u[5] if len(u) > 5 else "?"
            requests = u[7] if len(u) > 7 else "0"
            is_premium = "⭐" if len(u) > 10 and u[10] == "yes" else ""

            text += f"{is_premium}👤 <b>{first_name}</b> (@{username})\n"
            text += f"   ID: <code>{user_id}</code> | Запросов: {requests}\n"
            text += f"   Зарегистрирован: {first_seen}\n\n"

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error getting users: {e}")
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


@router.message(Command("broadcast"))
async def broadcast_command(message: types.Message) -> None:
    """Рассылка сообщения всем пользователям (только для админа)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    # Получаем текст после команды
    text_to_send = message.text.replace("/broadcast", "", 1).strip()

    if not text_to_send:
        await message.answer(
            "📢 <b>Рассылка</b>\n\n"
            "Использование:\n"
            "<code>/broadcast Ваше сообщение</code>\n\n"
            "Сообщение будет отправлено всем пользователям бота.",
            parse_mode="HTML"
        )
        return

    logger.info(f"Admin {message.from_user.id} starting broadcast")

    try:
        if not await sheets_manager.init():
            await message.answer("❌ Google Sheets недоступен.")
            return

        import asyncio
        loop = asyncio.get_event_loop()

        def get_user_ids():
            ws = sheets_manager.spreadsheet.worksheet("Users")
            users = ws.get_all_values()[1:]  # Skip header
            return [int(u[0]) for u in users if u[0].isdigit()]

        user_ids = await loop.run_in_executor(None, get_user_ids)

        if not user_ids:
            await message.answer("👥 Нет пользователей для рассылки.")
            return

        await message.answer(f"📢 Начинаю рассылку {len(user_ids)} пользователям...")

        sent = 0
        failed = 0

        for user_id in user_ids:
            try:
                await message.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 <b>Объявление</b>\n\n{text_to_send}",
                    parse_mode="HTML"
                )
                sent += 1
            except Exception as e:
                logger.debug(f"Failed to send to {user_id}: {e}")
                failed += 1

            # Задержка для избежания rate limit
            await asyncio.sleep(0.1)

        await message.answer(
            f"✅ <b>Рассылка завершена</b>\n\n"
            f"📤 Отправлено: {sent}\n"
            f"❌ Не доставлено: {failed}",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await message.answer(f"❌ Ошибка рассылки: {safe_format_error(e)}")


# ==================== INSTAGRAM COOKIES MANAGEMENT ====================

from src.utils.instagram_health import instagram_health, check_instagram_connection, update_cookies

# State for waiting cookies
_waiting_for_cookies = set()


@router.message(Command("checkinstagram"))
async def check_instagram_command(message: types.Message) -> None:
    """Проверить подключение к Instagram (только для админа)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    logger.info(f"Admin {message.from_user.id} requested Instagram check")
    
    status_msg = await message.answer("🔄 Проверяю подключение к Instagram...")
    
    is_working, check_message = await check_instagram_connection()
    
    if is_working:
        text = f"🟢 <b>Instagram Status: OK</b>\n\n{check_message}"
    else:
        text = (
            f"🔴 <b>Instagram Status: ERROR</b>\n\n"
            f"{check_message}\n\n"
            f"Для обновления cookies:\n"
            f"1. Отправьте /setcookies\n"
            f"2. Затем отправьте файл cookies или текст"
        )
    
    await status_msg.edit_text(text, parse_mode="HTML")


@router.message(Command("setcookies"))
async def setcookies_command(message: types.Message) -> None:
    """Начать процесс обновления cookies (только для админа)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    logger.info(f"Admin {message.from_user.id} started cookies update")
    
    _waiting_for_cookies.add(message.from_user.id)
    
    text = (
        "🍪 <b>Обновление Instagram Cookies</b>\n\n"
        "Отправьте cookies одним из способов:\n\n"
        "1️⃣ <b>Файл</b> - отправьте .txt файл с cookies\n"
        "2️⃣ <b>Текст</b> - вставьте содержимое cookies\n\n"
        "<i>Формат: Netscape HTTP Cookie File</i>\n\n"
        "Для отмены отправьте /cancel"
    )
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("cancel"))
async def cancel_command(message: types.Message) -> None:
    """Отменить ожидание cookies."""
    if message.from_user.id in _waiting_for_cookies:
        _waiting_for_cookies.discard(message.from_user.id)
        await message.answer("❌ Обновление cookies отменено.")
    else:
        await message.answer("Нечего отменять.")


# ==================== CALLBACK HANDLERS FOR PREMIUM ====================

@router.callback_query(lambda c: c.data and c.data.startswith("pay_"))
async def handle_payment_callback(callback: CallbackQuery) -> None:
    """Обработка нажатий на кнопки оплаты."""
    plan = callback.data.replace("pay_", "")

    plans = {
        "1month": ("1 месяц", "199 ₽"),
        "3month": ("3 месяца", "499 ₽"),
        "1year": ("1 год", "1499 ₽")
    }

    plan_name, plan_price = plans.get(plan, ("", ""))

    if not plan_name:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return

    text = (
        f"💳 <b>Оплата Premium — {plan_name}</b>\n\n"
        f"Сумма: <b>{plan_price}</b>\n\n"
        "Для оплаты:\n"
        "1️⃣ Напишите @smit_support\n"
        "2️⃣ Укажите выбранный тариф\n"
        "3️⃣ Получите реквизиты для оплаты\n"
        "4️⃣ После оплаты Premium активируется автоматически\n\n"
        "⏱️ Обычно активация занимает до 15 минут"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 Написать в поддержку", url="https://t.me/smit_support")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_premium")]
    ])

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_premium")
async def handle_back_to_premium_callback(callback: CallbackQuery) -> None:
    """Возврат к экрану Premium."""
    user_id = callback.from_user.id
    daily_count = await sheets_manager.get_user_daily_requests(user_id)

    text = (
        "💎 <b>Premium подписка</b>\n\n"
        f"📊 Сегодня использовано: {daily_count}/10 бесплатных скачиваний\n\n"
        "<b>Преимущества Premium:</b>\n"
        "✅ Безлимитные скачивания (без лимита 10/день)\n"
        "✅ HD качество YouTube (720p, 1080p)\n"
        "✅ Приоритетная очередь\n"
        "✅ Уникальные стили рерайта\n"
        "✅ Без рекламы\n\n"
        "<b>Тарифы:</b>\n"
        "📅 1 месяц — <b>199 ₽</b>\n"
        "📅 3 месяца — <b>499 ₽</b> <s>597 ₽</s>\n"
        "📅 1 год — <b>1499 ₽</b> <s>2388 ₽</s>\n\n"
        "💳 <b>Способы оплаты:</b>\n"
        "• Банковская карта (Visa/MasterCard/МИР)\n"
        "• СБП (Система быстрых платежей)\n"
        "• ЮMoney\n\n"
        "📩 Для оплаты напишите админу: @smit_support"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 1 месяц — 199 ₽", callback_data="pay_1month")],
        [InlineKeyboardButton(text="💳 Оплатить 3 месяца — 499 ₽", callback_data="pay_3month")],
        [InlineKeyboardButton(text="💳 Оплатить 1 год — 1499 ₽", callback_data="pay_1year")],
        [InlineKeyboardButton(text="📩 Написать в поддержку", url="https://t.me/smit_support")]
    ])

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "show_premium")
async def handle_show_premium_callback(callback: CallbackQuery) -> None:
    """Показать экран Premium из callback."""
    user_id = callback.from_user.id

    # Проверяем текущий статус пользователя
    is_premium = await sheets_manager.is_user_premium(user_id)

    if is_premium:
        text = (
            "⭐ <b>У вас уже есть Premium!</b>\n\n"
            "Вам доступны все функции:\n"
            "✅ Безлимитные скачивания\n"
            "✅ HD качество (720p, 1080p)\n"
            "✅ Приоритетная очередь\n"
            "✅ Без рекламы\n\n"
            "💎 Спасибо, что вы с нами!"
        )
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()
        return

    daily_count = await sheets_manager.get_user_daily_requests(user_id)

    text = (
        "💎 <b>Premium подписка</b>\n\n"
        f"📊 Сегодня использовано: {daily_count}/10 бесплатных скачиваний\n\n"
        "<b>Преимущества Premium:</b>\n"
        "✅ Безлимитные скачивания (без лимита 10/день)\n"
        "✅ HD качество YouTube (720p, 1080p)\n"
        "✅ Приоритетная очередь\n"
        "✅ Уникальные стили рерайта\n"
        "✅ Без рекламы\n\n"
        "<b>Тарифы:</b>\n"
        "📅 1 месяц — <b>199 ₽</b>\n"
        "📅 3 месяца — <b>499 ₽</b> <s>597 ₽</s>\n"
        "📅 1 год — <b>1499 ₽</b> <s>2388 ₽</s>\n\n"
        "💳 <b>Способы оплаты:</b>\n"
        "• Банковская карта (Visa/MasterCard/МИР)\n"
        "• СБП (Система быстрых платежей)\n"
        "• ЮMoney\n\n"
        "📩 Для оплаты напишите админу: @smit_support"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 1 месяц — 199 ₽", callback_data="pay_1month")],
        [InlineKeyboardButton(text="💳 Оплатить 3 месяца — 499 ₽", callback_data="pay_3month")],
        [InlineKeyboardButton(text="💳 Оплатить 1 год — 1499 ₽", callback_data="pay_1year")],
        [InlineKeyboardButton(text="📩 Написать в поддержку", url="https://t.me/smit_support")]
    ])

    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "show_platforms")
async def handle_show_platforms_callback(callback: CallbackQuery) -> None:
    """Показать список платформ из callback."""
    text = (
        "🌐 <b>Поддерживаемые платформы</b>\n\n"
        "📸 <b>Instagram</b>\n"
        "   • Фото и видео из постов\n"
        "   • Reels\n"
        "   • Карусели (несколько фото/видео)\n\n"
        "🎵 <b>TikTok</b>\n"
        "   • Видео без водяного знака\n\n"
        "🎥 <b>YouTube</b>\n"
        "   • Видео (360p бесплатно, HD для Premium)\n"
        "   • Shorts\n"
        "   • Аудио (MP3)\n\n"
        "🐦 <b>Twitter / X</b>\n"
        "   • Видео из твитов\n"
        "   • Фото\n"
        "   • GIF\n\n"
        "📘 <b>Facebook</b>\n"
        "   • Публичные видео\n"
        "   • Reels\n\n"
        "💡 <b>Как пользоваться:</b>\n"
        "Просто отправьте ссылку на пост — бот всё скачает автоматически!"
    )

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(lambda msg: msg.from_user.id in _waiting_for_cookies and msg.document)
async def receive_cookies_file(message: types.Message) -> None:
    """Получить файл с cookies."""
    logger.info(f"Admin {message.from_user.id} sent cookies file")
    
    try:
        # Download file
        file = await message.bot.get_file(message.document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        cookies_text = file_content.read().decode('utf-8')
        
        status_msg = await message.answer("🔄 Обновляю cookies...")
        
        success, result_message = await update_cookies(cookies_text)
        
        _waiting_for_cookies.discard(message.from_user.id)
        
        if success:
            await status_msg.edit_text(f"✅ {result_message}", parse_mode="HTML")
        else:
            await status_msg.edit_text(f"❌ {result_message}", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Error processing cookies file: {e}")
        await message.answer(f"❌ Ошибка обработки файла: {safe_format_error(e)}")


@router.message(lambda msg: msg.from_user.id in _waiting_for_cookies and msg.text and not msg.text.startswith('/'))
async def receive_cookies_text(message: types.Message) -> None:
    """Получить текст cookies."""
    logger.info(f"Admin {message.from_user.id} sent cookies text")
    
    cookies_text = message.text
    
    # Basic validation
    if "instagram.com" not in cookies_text.lower():
        await message.answer(
            "❌ Это не похоже на Instagram cookies.\n"
            "Убедитесь, что отправляете cookies в формате Netscape."
        )
        return
    
    status_msg = await message.answer("🔄 Обновляю cookies...")
    
    success, result_message = await update_cookies(cookies_text)
    
    _waiting_for_cookies.discard(message.from_user.id)
    
    if success:
        await status_msg.edit_text(f"✅ {result_message}", parse_mode="HTML")
    else:
        await status_msg.edit_text(f"❌ {result_message}", parse_mode="HTML")


# ==================== CALLBACK HANDLERS ====================

@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery) -> None:
    """Показать админ-панель через callback."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к этой панели.", show_alert=True)
        return

    logger.info(f"Admin {callback.from_user.id} opened admin panel via callback")

    text = (
        "👑 <b>Админ-панель</b>\n\n"
        "<b>Доступные команды:</b>\n\n"
        "/admin - 👑 Админ-панель\n"
        "/allstats - 📈 Общая статистика бота\n"
        "/users - 👥 Список пользователей\n"
        "/broadcast - 📢 Рассылка всем\n"
        "/checkinstagram - 🔍 Проверить Instagram\n"
        "/setcookies - 🍪 Обновить cookies\n\n"
        "<b>Ссылки:</b>\n"
        "📊 <a href='https://docs.google.com/spreadsheets/d/1cQhOc-FyY5uF7cLC2nH0jht2pITrt0bc3swhvfhVUoI/'>Google Sheets</a>\n"
        "💬 <a href='https://t.me/c/3307715316/'>Супергруппа уведомлений</a>"
    )

    # Создаём кнопки для быстрого доступа
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="🔍 Проверить Instagram", callback_data="admin_check_ig"),
            InlineKeyboardButton(text="🍪 Обновить cookies", callback_data="admin_set_cookies")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")
        ]
    ])

    await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start_callback(callback: CallbackQuery) -> None:
    """Вернуться к стартовому сообщению."""
    from src.localization.messages import START_WELCOME

    user_id = callback.from_user.id

    # Кнопки быстрого доступа (как в /start)
    if user_id == config.ADMIN_ID:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 Платформы", callback_data="show_platforms"),
                InlineKeyboardButton(text="💎 Premium", callback_data="show_premium")
            ],
            [
                InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")
            ],
            [
                InlineKeyboardButton(text="📤 Поделиться ботом", switch_inline_query="Качай видео с Instagram, TikTok, YouTube!")
            ]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 Платформы", callback_data="show_platforms"),
                InlineKeyboardButton(text="💎 Premium", callback_data="show_premium")
            ],
            [
                InlineKeyboardButton(text="📤 Поделиться ботом", switch_inline_query="Качай видео с Instagram, TikTok, YouTube!")
            ]
        ])

    await callback.message.edit_text(START_WELCOME, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery) -> None:
    """Показать статистику через callback."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.answer("📊 Получаю статистику...")

    # Используем код из allstats_command
    try:
        import asyncio
        loop = asyncio.get_event_loop()

        def get_stats():
            data = sheets_manager.sheet.get_all_records()
            if not data:
                return None

            total_users = len(set(record.get("user_id") for record in data if record.get("user_id")))
            premium_users = len(set(
                record.get("user_id") for record in data
                if record.get("user_id") and record.get("is_premium") == "TRUE"
            ))
            total_requests = len([r for r in data if r.get("platform")])
            successful = len([r for r in data if r.get("status") == "success"])

            platforms = {}
            for record in data:
                platform = record.get("platform")
                if platform:
                    platforms[platform] = platforms.get(platform, 0) + 1

            return {
                "total_users": total_users,
                "premium_users": premium_users,
                "total_requests": total_requests,
                "successful": successful,
                "platforms": platforms
            }

        stats = await loop.run_in_executor(None, get_stats)

        if not stats:
            await callback.message.answer("❌ Нет данных для отображения статистики.")
            return

        success_rate = (stats["successful"] / stats["total_requests"] * 100) if stats["total_requests"] > 0 else 0

        platform_text = "\n".join([
            f"  • {p}: {c}" for p, c in sorted(stats["platforms"].items(), key=lambda x: -x[1])
        ]) or "  Нет данных"

        text = (
            "📈 <b>Общая статистика</b>\n\n"
            f"👥 <b>Пользователи:</b> {stats['total_users']}\n"
            f"  ⭐ Premium: {stats['premium_users']}\n\n"
            f"📥 <b>Запросы:</b> {stats['total_requests']}\n"
            f"  ✅ Успешных: {stats['successful']} ({success_rate:.1f}%)\n"
            f"  ❌ Ошибок: {stats['total_requests'] - stats['successful']}\n\n"
            f"📊 <b>По платформам:</b>\n{platform_text}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
        ])

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error getting stats in callback: {e}")
        await callback.message.answer(f"❌ Ошибка: {safe_format_error(e)}")


@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery) -> None:
    """Показать список пользователей через callback."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.answer("👥 Получаю список пользователей...")

    try:
        import asyncio
        loop = asyncio.get_event_loop()

        def get_users():
            data = sheets_manager.sheet.get_all_records()
            if not data:
                return []

            users_dict = {}
            for record in data:
                user_id = record.get("user_id")
                if not user_id:
                    continue

                if user_id not in users_dict:
                    users_dict[user_id] = {
                        "username": record.get("username", "н/д"),
                        "first_name": record.get("first_name", ""),
                        "last_name": record.get("last_name", ""),
                        "is_premium": record.get("is_premium") == "TRUE",
                        "first_seen": record.get("first_seen", ""),
                        "request_count": 0
                    }

                if record.get("platform"):
                    users_dict[user_id]["request_count"] += 1

            return sorted(users_dict.items(), key=lambda x: x[1]["request_count"], reverse=True)

        users = await loop.run_in_executor(None, get_users)

        if not users:
            text = "👥 <b>Пользователи</b>\n\nПользователей пока нет."
        else:
            users_list = []
            for i, (user_id, info) in enumerate(users[:20], 1):  # Показываем топ-20
                name = info["first_name"] or info["username"] or "Без имени"
                premium = "⭐" if info["is_premium"] else ""
                users_list.append(
                    f"{i}. {premium} <code>{user_id}</code> - {name} ({info['request_count']} зап.)"
                )

            text = (
                f"👥 <b>Пользователи</b> (топ-20)\n\n"
                f"Всего: {len(users)}\n\n" +
                "\n".join(users_list)
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
        ])

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error getting users in callback: {e}")
        await callback.message.answer(f"❌ Ошибка: {safe_format_error(e)}")


@router.callback_query(lambda c: c.data == "admin_check_ig")
async def admin_check_ig_callback(callback: CallbackQuery) -> None:
    """Проверка Instagram через callback."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.answer("🔍 Используйте команду /checkinstagram для проверки", show_alert=True)


@router.callback_query(lambda c: c.data == "admin_set_cookies")
async def admin_set_cookies_callback(callback: CallbackQuery) -> None:
    """Обновление cookies через callback."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.answer("🍪 Используйте команду /setcookies для обновления cookies", show_alert=True)


# ==================== НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ ====================

@router.callback_query(lambda c: c.data == "settings_quality")
async def settings_quality_callback(callback: CallbackQuery) -> None:
    """Изменить качество по умолчанию."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="360p", callback_data="set_quality_360p")],
        [InlineKeyboardButton(text="480p", callback_data="set_quality_480p")],
        [InlineKeyboardButton(text="720p", callback_data="set_quality_720p")],
        [InlineKeyboardButton(text="1080p (Premium)", callback_data="set_quality_1080p")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_settings")]
    ])

    text = (
        "🎬 <b>Выберите качество по умолчанию</b>\n\n"
        "Это качество будет использоваться автоматически при скачивании YouTube видео.\n\n"
        "💡 Для Instagram и TikTok всегда используется максимальное качество."
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("set_quality_"))
async def set_quality_callback(callback: CallbackQuery) -> None:
    """Установить качество."""
    quality = callback.data.replace("set_quality_", "")
    user_id = callback.from_user.id

    # Проверяем Premium для 1080p
    if quality == "1080p":
        is_premium = await sheets_manager.is_user_premium(user_id)
        if not is_premium:
            await callback.answer(
                "❌ Качество 1080p доступно только для Premium пользователей",
                show_alert=True
            )
            return

    db = get_db_manager()
    if db:
        success = await db.update_user_settings(user_id, default_quality=quality)
        if success:
            await callback.answer(f"✅ Качество изменено на {quality}")
            # Возврат к настройкам
            await settings_command(callback.message)
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
    else:
        await callback.answer("❌ Настройки недоступны", show_alert=True)


@router.callback_query(lambda c: c.data == "settings_format")
async def settings_format_callback(callback: CallbackQuery) -> None:
    """Изменить формат по умолчанию."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="MP4 (рекомендуется)", callback_data="set_format_mp4")],
        [InlineKeyboardButton(text="WebM", callback_data="set_format_webm")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_settings")]
    ])

    text = (
        "📁 <b>Выберите формат видео</b>\n\n"
        "<b>MP4:</b> Универсальный формат, работает везде\n"
        "<b>WebM:</b> Меньший размер, но не все плееры поддерживают\n\n"
        "💡 Рекомендуем MP4 для совместимости"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("set_format_"))
async def set_format_callback(callback: CallbackQuery) -> None:
    """Установить формат."""
    format_type = callback.data.replace("set_format_", "")
    user_id = callback.from_user.id

    db = get_db_manager()
    if db:
        success = await db.update_user_settings(user_id, default_format=format_type)
        if success:
            await callback.answer(f"✅ Формат изменен на {format_type.upper()}")
            await settings_command(callback.message)
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
    else:
        await callback.answer("❌ Настройки недоступны", show_alert=True)


@router.callback_query(lambda c: c.data == "settings_autodelete")
async def settings_autodelete_callback(callback: CallbackQuery) -> None:
    """Изменить время авто-удаления."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="3 дня", callback_data="set_autodelete_3")],
        [InlineKeyboardButton(text="7 дней", callback_data="set_autodelete_7")],
        [InlineKeyboardButton(text="14 дней", callback_data="set_autodelete_14")],
        [InlineKeyboardButton(text="30 дней", callback_data="set_autodelete_30")],
        [InlineKeyboardButton(text="Никогда", callback_data="set_autodelete_999")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_settings")]
    ])

    text = (
        "🗑️ <b>Авто-удаление файлов</b>\n\n"
        "Через сколько дней удалять скачанные файлы с сервера?\n\n"
        "💡 Это не влияет на вашу историю - только на файлы на сервере"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("set_autodelete_"))
async def set_autodelete_callback(callback: CallbackQuery) -> None:
    """Установить время авто-удаления."""
    days = int(callback.data.replace("set_autodelete_", ""))
    user_id = callback.from_user.id

    db = get_db_manager()
    if db:
        success = await db.update_user_settings(user_id, auto_delete_after_days=days)
        if success:
            days_text = "никогда" if days == 999 else f"через {days} дней"
            await callback.answer(f"✅ Файлы будут удаляться {days_text}")
            await settings_command(callback.message)
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
    else:
        await callback.answer("❌ Настройки недоступны", show_alert=True)


@router.callback_query(lambda c: c.data == "settings_notifications")
async def settings_notifications_callback(callback: CallbackQuery) -> None:
    """Переключить уведомления."""
    user_id = callback.from_user.id

    db = get_db_manager()
    if db:
        settings = await db.get_user_settings(user_id)
        new_value = not settings['notifications_enabled']

        success = await db.update_user_settings(user_id, notifications_enabled=new_value)
        if success:
            status = "включены" if new_value else "выключены"
            await callback.answer(f"✅ Уведомления {status}")
            await settings_command(callback.message)
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
    else:
        await callback.answer("❌ Настройки недоступны", show_alert=True)


@router.callback_query(lambda c: c.data == "back_to_settings")
async def back_to_settings_callback(callback: CallbackQuery) -> None:
    """Вернуться к настройкам."""
    await settings_command(callback.message)
    await callback.answer()


# ==================== ИСТОРИЯ ЗАГРУЗОК ====================

@router.callback_query(lambda c: c.data.startswith("history_redownload_"))
async def history_redownload_callback(callback: CallbackQuery) -> None:
    """Повторная загрузка из истории."""
    try:
        download_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id

        db = get_db_manager()
        if not db:
            await callback.answer("❌ История недоступна", show_alert=True)
            return

        # Получаем запись из истории
        item = await db.get_download_by_id(download_id)

        if not item or item['user_id'] != user_id:
            await callback.answer("❌ Элемент не найден", show_alert=True)
            return

        # Проверяем, существует ли файл на диске
        file_path = item.get('file_path')
        if file_path and os.path.exists(file_path):
            # Файл есть - отправляем из кэша
            try:
                # Определяем тип файла
                if file_path.endswith(('.mp4', '.mov', '.avi', '.webm')):
                    await callback.message.answer_video(
                        types.FSInputFile(file_path),
                        caption=f"📂 Из истории: {item['title'] or 'Видео'}"
                    )
                elif file_path.endswith(('.mp3', '.m4a', '.wav')):
                    await callback.message.answer_audio(
                        types.FSInputFile(file_path),
                        caption=f"📂 Из истории: {item['title'] or 'Аудио'}"
                    )
                elif file_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    await callback.message.answer_photo(
                        types.FSInputFile(file_path),
                        caption=f"📂 Из истории: {item['title'] or 'Фото'}"
                    )
                else:
                    await callback.message.answer_document(
                        types.FSInputFile(file_path),
                        caption=f"📂 Из истории: {item['title'] or 'Файл'}"
                    )

                await callback.answer("✅ Отправлено из кэша")
                logger.info(f"Resent from cache: {file_path}")
            except Exception as e:
                logger.error(f"Failed to resend file: {e}")
                # Файл поврежден или недоступен - скачиваем заново
                await callback.answer("⏳ Файл недоступен, скачиваю заново...")
                await callback.message.answer(item['url'])
        else:
            # Файла нет - скачиваем заново, отправляя URL в обработчик
            await callback.answer("⏳ Скачиваю заново...")
            await callback.message.answer(item['url'])

    except Exception as e:
        logger.error(f"Error in redownload callback: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("history_favorite_"))
async def history_favorite_callback(callback: CallbackQuery) -> None:
    """Добавить в избранное из истории."""
    try:
        download_id = int(callback.data.split("_")[-1])

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        success = await db.add_to_favorites(download_id)
        if success:
            await callback.answer("⭐ Добавлено в избранное")
            # Обновляем сообщение
            await history_command(callback.message)
        else:
            await callback.answer("❌ Ошибка", show_alert=True)

    except Exception as e:
        logger.error(f"Error adding to favorites: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("history_unfavorite_"))
async def history_unfavorite_callback(callback: CallbackQuery) -> None:
    """Удалить из избранного."""
    try:
        download_id = int(callback.data.split("_")[-1])

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        success = await db.remove_from_favorites(download_id)
        if success:
            await callback.answer("💔 Удалено из избранного")
            # Обновляем сообщение
            await history_command(callback.message)
        else:
            await callback.answer("❌ Ошибка", show_alert=True)

    except Exception as e:
        logger.error(f"Error removing from favorites: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("history_show_more_"))
async def history_show_more_callback(callback: CallbackQuery) -> None:
    """Показать больше записей истории."""
    try:
        offset = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id

        db = get_db_manager()
        if not db:
            await callback.answer("❌ История недоступна", show_alert=True)
            return

        # Получаем следующие 10 записей
        history = await db.get_download_history(user_id, limit=10, offset=offset)

        if not history:
            await callback.answer("📭 Больше записей нет", show_alert=True)
            return

        platform_emoji = {
            "Instagram": "📸",
            "YouTube": "📺",
            "TikTok": "🎵",
            "VK": "🎬",
            "Twitter": "🐦",
            "X": "🐦"
        }

        items = []
        for i, item in enumerate(history, offset + 1):
            emoji = platform_emoji.get(item['platform'], "📁")

            try:
                date = datetime.fromisoformat(item['download_date'])
                date_str = date.strftime("%d.%m %H:%M")
            except:
                date_str = "недавно"

            title = (item['title'] or "Без названия")[:35]
            if len(item['title'] or "") > 35:
                title += "..."

            file_size = item['file_size'] or 0
            size_mb = file_size / 1024 / 1024 if file_size > 0 else 0

            favorite_mark = "⭐ " if item['is_favorite'] else ""
            items.append(
                f"{i}. {emoji} {favorite_mark}<b>{title}</b>\n"
                f"   {date_str} • {size_mb:.1f} MB"
            )

        text = (
            f"📂 <b>История загрузок (записи {offset + 1}-{offset + len(history)})</b>\n\n" +
            "\n\n".join(items)
        )

        # Кнопка "Показать еще" если есть больше записей
        buttons = []
        if len(history) >= 10:
            buttons.append([InlineKeyboardButton(
                text="📊 Показать еще",
                callback_data=f"history_show_more_{offset + 10}"
            )])

        buttons.append([InlineKeyboardButton(
            text="« Назад к началу",
            callback_data="show_history"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing more history: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data == "show_history")
async def show_history_callback(callback: CallbackQuery) -> None:
    """Показать историю (callback для главного меню)."""
    await history_command(callback.message)
    await callback.answer()


# ==================== ИЗБРАННОЕ ====================

@router.callback_query(lambda c: c.data.startswith("fav_download_"))
async def fav_download_callback(callback: CallbackQuery) -> None:
    """Скачать из избранного."""
    try:
        download_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        # Получаем запись
        item = await db.get_download_by_id(download_id)

        if not item or item['user_id'] != user_id:
            await callback.answer("❌ Элемент не найден", show_alert=True)
            return

        # Проверяем файл
        file_path = item.get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                # Отправляем из кэша
                if file_path.endswith(('.mp4', '.mov', '.avi', '.webm')):
                    await callback.message.answer_video(
                        types.FSInputFile(file_path),
                        caption=f"⭐ Из избранного: {item['title'] or 'Видео'}"
                    )
                elif file_path.endswith(('.mp3', '.m4a', '.wav')):
                    await callback.message.answer_audio(
                        types.FSInputFile(file_path),
                        caption=f"⭐ Из избранного: {item['title'] or 'Аудио'}"
                    )
                elif file_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    await callback.message.answer_photo(
                        types.FSInputFile(file_path),
                        caption=f"⭐ Из избранного: {item['title'] or 'Фото'}"
                    )
                else:
                    await callback.message.answer_document(
                        types.FSInputFile(file_path),
                        caption=f"⭐ Из избранного: {item['title'] or 'Файл'}"
                    )

                await callback.answer("✅ Отправлено из кэша")
            except Exception as e:
                logger.error(f"Failed to resend file: {e}")
                await callback.answer("⏳ Скачиваю заново...")
                await callback.message.answer(item['url'])
        else:
            # Скачиваем заново
            await callback.answer("⏳ Скачиваю заново...")
            await callback.message.answer(item['url'])

    except Exception as e:
        logger.error(f"Error in fav_download callback: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("fav_remove_"))
async def fav_remove_callback(callback: CallbackQuery) -> None:
    """Удалить из избранного."""
    try:
        download_id = int(callback.data.split("_")[-1])

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        success = await db.remove_from_favorites(download_id)
        if success:
            await callback.answer("💔 Удалено из избранного")
            # Обновляем список избранного
            await favorites_command(callback.message)
        else:
            await callback.answer("❌ Ошибка", show_alert=True)

    except Exception as e:
        logger.error(f"Error removing from favorites: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data == "favorites_show_all")
async def favorites_show_all_callback(callback: CallbackQuery) -> None:
    """Показать все избранные."""
    try:
        user_id = callback.from_user.id

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        # Получаем все избранные
        favorites = await db.get_download_history(user_id, limit=100, favorites_only=True)

        if not favorites:
            await callback.answer("📭 Избранное пусто", show_alert=True)
            return

        platform_emoji = {
            "Instagram": "📸",
            "YouTube": "📺",
            "TikTok": "🎵",
            "VK": "🎬",
            "Twitter": "🐦",
            "X": "🐦"
        }

        items = []
        for i, item in enumerate(favorites[:20], 1):
            emoji = platform_emoji.get(item['platform'], "📁")

            try:
                date = datetime.fromisoformat(item['download_date'])
                date_str = date.strftime("%d.%m")
            except:
                date_str = "недавно"

            title = (item['title'] or "Без названия")[:30]
            if len(item['title'] or "") > 30:
                title += "..."

            items.append(f"{i}. {emoji} {title} ({date_str})")

        text = (
            f"⭐ <b>Все избранное ({len(favorites)})</b>\n\n" +
            "\n".join(items)
        )

        if len(favorites) > 20:
            text += f"\n\n...и еще {len(favorites) - 20}"

        await callback.message.edit_text(text, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing all favorites: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)
