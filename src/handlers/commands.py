"""Handler for user and admin commands."""
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from src.utils.logger import get_logger
from src.utils.sheets import sheets_manager
from src.config import config

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


# ==================== АДМИНСКИЕ КОМАНДЫ ====================

@router.message(Command("admin"))
async def admin_command(message: types.Message) -> None:
    """Админ-панель."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    logger.info(f"Admin {message.from_user.id} opened admin panel")

    text = (
        "👑 <b>Админ-панель</b>\n\n"
        "<b>Доступные команды:</b>\n\n"
        "/allstats - 📈 Общая статистика бота\n"
        "/users - 👥 Список пользователей\n"
        "/broadcast <текст> - 📢 Рассылка всем\n"
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
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")


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
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")


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
        await message.answer(f"❌ Ошибка рассылки: {str(e)[:100]}")


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
        await message.answer(f"❌ Ошибка обработки файла: {str(e)[:100]}")


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
