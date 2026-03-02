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
from src.utils.rate_limiter import rate_limiter
from src.utils.history_exporter import export_user_history, HistoryExporter
from src.utils.history_search import HistorySearcher

logger = get_logger(__name__)
router = Router()

# State для поиска
search_state = {}


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id == config.ADMIN_ID


# ==================== ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ====================

# Обработчик текстовых сообщений для создания коллекции
@router.message(lambda msg: msg.from_user.id in collection_creation_state and not msg.text.startswith('/'))
async def handle_collection_name(message: types.Message) -> None:
    """Обработать название новой коллекции."""
    user_id = message.from_user.id

    if user_id not in collection_creation_state:
        return

    try:
        db = get_db_manager()
        if not db:
            await message.answer("❌ Ошибка создания коллекции")
            del collection_creation_state[user_id]
            return

        collection_name = message.text.strip()

        # Проверяем наличие эмодзи в начале
        icon = "📁"
        name = collection_name

        # Простая проверка на эмодзи (первый символ)
        if collection_name and len(collection_name) > 1:
            first_char = collection_name[0]
            # Если первый символ эмодзи (не латиница, не кириллица, не цифра)
            if not first_char.isalnum():
                icon = first_char
                name = collection_name[1:].strip()

        # Создаем коллекцию
        collection_id = await db.create_collection(
            user_id=user_id,
            name=name,
            description=None,
            icon=icon
        )

        if collection_id:
            await message.answer(
                f"✅ Коллекция создана!\n\n{icon} <b>{name}</b>\n\n"
                f"💡 Теперь вы можете добавлять загрузки в эту коллекцию через /history",
                parse_mode="HTML"
            )

            # Очищаем состояние
            del collection_creation_state[user_id]

            # Показываем список коллекций
            await collections_command(message)
        else:
            await message.answer("❌ Ошибка создания коллекции")
            del collection_creation_state[user_id]

    except Exception as e:
        logger.error(f"Error creating collection: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")
        if user_id in collection_creation_state:
            del collection_creation_state[user_id]


@router.message(Command("mystats"))
async def mystats_command(message: types.Message) -> None:
    """Показать расширенную статистику пользователя из базы."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested mystats")

    try:
        db = get_db_manager()
        if not db:
            await message.answer("⚠️ Статистика временно недоступна")
            return

        # Получаем данные из базы
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # Всего загрузок
        cursor.execute("SELECT COUNT(*) FROM download_history WHERE user_id = ?", (user_id,))
        total_downloads = cursor.fetchone()[0]

        if total_downloads == 0:
            await message.answer(
                "📊 <b>Моя статистика</b>\n\n"
                "У вас пока нет загрузок.\n\n"
                "💡 Отправьте ссылку на пост из Instagram, YouTube или TikTok!",
                parse_mode="HTML"
            )
            conn.close()
            return

        # По платформам
        cursor.execute("""
            SELECT platform, COUNT(*) as count
            FROM download_history
            WHERE user_id = ?
            GROUP BY platform
            ORDER BY count DESC
        """, (user_id,))
        platforms = cursor.fetchall()

        # Любимая платформа
        favorite_platform = platforms[0] if platforms else ("Нет", 0)
        favorite_percentage = (favorite_platform[1] / total_downloads * 100) if total_downloads > 0 else 0

        # Скачано данных
        cursor.execute("SELECT SUM(file_size) FROM download_history WHERE user_id = ?", (user_id,))
        total_bytes = cursor.fetchone()[0] or 0
        total_gb = total_bytes / (1024 * 1024 * 1024)

        # Избранное
        cursor.execute("SELECT COUNT(*) FROM download_history WHERE user_id = ? AND is_favorite = 1", (user_id,))
        favorites = cursor.fetchone()[0]

        # Коллекции
        cursor.execute("SELECT COUNT(*) FROM collections WHERE user_id = ?", (user_id,))
        collections = cursor.fetchone()[0]

        # Активность по дням недели
        cursor.execute("""
            SELECT strftime('%w', download_date) as dow, COUNT(*) as count
            FROM download_history
            WHERE user_id = ?
            GROUP BY dow
            ORDER BY dow
        """, (user_id,))
        activity_by_dow = dict(cursor.fetchall())

        # Последняя загрузка
        cursor.execute("""
            SELECT download_date, platform, title
            FROM download_history
            WHERE user_id = ?
            ORDER BY download_date DESC
            LIMIT 1
        """, (user_id,))
        last_download = cursor.fetchone()

        conn.close()

        # Форматируем платформы
        platform_icons = {
            "Instagram": "📸",
            "YouTube": "📺",
            "TikTok": "🎵",
            "VK": "🎬",
            "Twitter": "🐦"
        }

        platform_text = "\n".join([
            f"  {platform_icons.get(p, '📁')} {p}: {c} ({c/total_downloads*100:.0f}%)"
            for p, c in platforms[:5]
        ])

        # График активности по дням
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        max_count = max(activity_by_dow.values()) if activity_by_dow else 1

        activity_graph = []
        for i in range(7):
            dow_str = str((i + 1) % 7)  # 0=Вс, 1=Пн, ..., 6=Сб
            count = activity_by_dow.get(dow_str, 0)
            bars = int(count / max_count * 10) if max_count > 0 else 0
            bar_graph = "▓" * bars + "░" * (10 - bars)
            activity_graph.append(f"{days[i]} {bar_graph} {count}")

        activity_text = "\n".join(activity_graph)

        # Последняя загрузка
        last_text = "Нет данных"
        if last_download:
            try:
                last_date = datetime.fromisoformat(last_download[0])
                last_date_str = last_date.strftime("%d.%m.%Y %H:%M")
                last_title = (last_download[2] or "Без названия")[:30]
                last_text = f"{platform_icons.get(last_download[1], '📁')} {last_title}\n  {last_date_str}"
            except:
                last_text = "Недавно"

        text = (
            "📊 <b>Моя статистика</b>\n\n"

            f"🎬 <b>Всего загрузок:</b> {total_downloads}\n"
            f"📸 <b>Любимая платформа:</b> {favorite_platform[0]} ({favorite_percentage:.0f}%)\n"
            f"💾 <b>Скачано данных:</b> {total_gb:.2f} GB\n"
            f"⭐ <b>В избранном:</b> {favorites}\n"
            f"📁 <b>Коллекций:</b> {collections}\n\n"

            f"<b>📊 По платформам:</b>\n{platform_text}\n\n"

            f"<b>📈 Активность по дням:</b>\n<code>{activity_text}</code>\n\n"

            f"<b>⏱️ Последняя загрузка:</b>\n{last_text}"
        )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in mystats: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


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
                row1 = []
                row1.append(InlineKeyboardButton(
                    text=f"{i}. Скачать снова",
                    callback_data=f"history_redownload_{item['id']}"
                ))

                # Кнопка избранного (добавить или удалить)
                if item['is_favorite']:
                    row1.append(InlineKeyboardButton(
                        text="💔",
                        callback_data=f"history_unfavorite_{item['id']}"
                    ))
                else:
                    row1.append(InlineKeyboardButton(
                        text="⭐",
                        callback_data=f"history_favorite_{item['id']}"
                    ))

                row1.append(InlineKeyboardButton(
                    text="📁",
                    callback_data=f"history_add_to_collection_{item['id']}"
                ))

                buttons.append(row1)

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

        # Добавляем кнопки поиска и экспорта
        buttons.append([
            InlineKeyboardButton(
                text="🔍 Поиск",
                callback_data="open_search"
            ),
            InlineKeyboardButton(
                text="📤 Экспорт",
                callback_data="export_menu_from_history"
            )
        ])

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


@router.message(Command("collections"))
async def collections_command(message: types.Message) -> None:
    """Показать коллекции пользователя."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested collections")

    try:
        db = get_db_manager()
        if not db:
            await message.answer("⚠️ Коллекции временно недоступны")
            return

        # Получаем все коллекции пользователя
        collections = await db.get_collections(user_id)

        if not collections:
            text = (
                "📁 <b>Коллекции</b>\n\n"
                "У вас пока нет коллекций.\n\n"
                "💡 Создайте коллекцию для организации своих загрузок!"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="➕ Создать коллекцию",
                    callback_data="collection_create"
                )]
            ])
            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
            return

        # Формируем список коллекций
        items = []
        buttons = []

        for i, collection in enumerate(collections[:10], 1):
            icon = collection.get('icon', '📁')
            name = collection.get('name', 'Без названия')

            # Получаем количество элементов в коллекции
            items_in_collection = await db.get_collection_items(collection['id'])
            count = len(items_in_collection)

            items.append(f"{i}. {icon} <b>{name}</b> ({count} шт.)")

            # Кнопки для коллекций
            row = []
            row.append(InlineKeyboardButton(
                text=f"{i}. Открыть",
                callback_data=f"collection_open_{collection['id']}"
            ))
            row.append(InlineKeyboardButton(
                text="✏️",
                callback_data=f"collection_edit_{collection['id']}"
            ))
            row.append(InlineKeyboardButton(
                text="🗑️",
                callback_data=f"collection_delete_{collection['id']}"
            ))
            buttons.append(row)

        # Кнопка создания новой коллекции
        buttons.append([InlineKeyboardButton(
            text="➕ Создать новую коллекцию",
            callback_data="collection_create"
        )])

        text = (
            f"📁 <b>Мои коллекции ({len(collections)})</b>\n\n" +
            "\n".join(items)
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in collections command: {e}", exc_info=True)
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

        # Получаем данные из базы
        db_stats = {}
        db = get_db_manager()
        if db:
            # Общее количество загрузок в базе
            conn = db.db_path
            import sqlite3
            db_conn = sqlite3.connect(conn)
            cursor = db_conn.cursor()

            # Всего загрузок
            cursor.execute("SELECT COUNT(*) FROM download_history")
            total_downloads = cursor.fetchone()[0]

            # По платформам
            cursor.execute("""
                SELECT platform, COUNT(*) as count
                FROM download_history
                GROUP BY platform
                ORDER BY count DESC
            """)
            db_platforms = dict(cursor.fetchall())

            # Избранное
            cursor.execute("SELECT COUNT(*) FROM download_history WHERE is_favorite = 1")
            favorites_count = cursor.fetchone()[0]

            # Коллекции
            cursor.execute("SELECT COUNT(*) FROM collections")
            collections_count = cursor.fetchone()[0]

            # Настройки пользователей
            cursor.execute("SELECT COUNT(*) FROM user_settings")
            users_with_settings = cursor.fetchone()[0]

            # Популярные качества
            cursor.execute("""
                SELECT default_quality, COUNT(*) as count
                FROM user_settings
                GROUP BY default_quality
                ORDER BY count DESC
                LIMIT 3
            """)
            popular_qualities = cursor.fetchall()

            db_conn.close()

            db_stats = {
                "total_downloads": total_downloads,
                "platforms": db_platforms,
                "favorites": favorites_count,
                "collections": collections_count,
                "users_with_settings": users_with_settings,
                "popular_qualities": popular_qualities
            }

        success_rate = (stats["successful"] / stats["total_requests"] * 100) if stats["total_requests"] > 0 else 0

        # Format platforms from Google Sheets
        platform_text = "\n".join([
            f"  • {p}: {c}" for p, c in sorted(stats["platforms"].items(), key=lambda x: -x[1])[:5]
        ]) or "  Нет данных"

        # Format DB platforms
        db_platform_text = ""
        if db_stats and db_stats.get("platforms"):
            db_platform_text = "\n".join([
                f"  • {p}: {c}" for p, c in list(db_stats["platforms"].items())[:5]
            ])

        # Format qualities
        quality_text = ""
        if db_stats and db_stats.get("popular_qualities"):
            quality_text = ", ".join([
                f"{q[0]} ({q[1]})" for q in db_stats["popular_qualities"]
            ])

        text = (
            "📈 <b>Общая статистика бота</b>\n\n"

            "<b>👥 Пользователи:</b>\n"
            f"  Всего: {stats['total_users']}\n"
            f"  ⭐ Premium: {stats['premium_users']}\n"
            f"  ⚙️ С настройками: {db_stats.get('users_with_settings', 0)}\n\n"

            "<b>📥 Запросы (Google Sheets):</b>\n"
            f"  Всего: {stats['total_requests']}\n"
            f"  ✅ Успешных: {stats['successful']} ({success_rate:.1f}%)\n"
            f"  ❌ Ошибок: {stats['total_requests'] - stats['successful']}\n\n"

            "<b>📊 Платформы (Sheets):</b>\n"
            f"{platform_text}\n\n"
        )

        if db_stats:
            text += (
                "<b>💾 База данных:</b>\n"
                f"  📂 Загрузок в истории: {db_stats.get('total_downloads', 0)}\n"
                f"  ⭐ В избранном: {db_stats.get('favorites', 0)}\n"
                f"  📁 Коллекций: {db_stats.get('collections', 0)}\n\n"
            )

            if db_platform_text:
                text += f"<b>📊 Платформы (DB):</b>\n{db_platform_text}\n\n"

            if quality_text:
                text += f"<b>🎬 Популярные качества:</b>\n  {quality_text}\n\n"

        # Добавляем rate limiter stats
        rl_stats = rate_limiter.get_stats()
        total_rl_requests = sum(s['request_count'] for s in rl_stats.values())
        if total_rl_requests > 0:
            text += (
                f"<b>⏱️ Rate Limiter:</b>\n"
                f"  Запросов: {total_rl_requests}\n"
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


@router.message(Command("ratelimit"))
async def ratelimit_command(message: types.Message) -> None:
    """Показать статистику rate limiter (только админ)."""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    try:
        stats = rate_limiter.get_stats()

        lines = ["📊 <b>Статистика Rate Limiter</b>\n"]

        for platform, data in stats.items():
            if data['request_count'] == 0:
                continue

            icon_map = {
                "instagram": "📸",
                "youtube": "📺",
                "tiktok": "🎵",
                "vk": "🎬",
                "twitter": "🐦",
                "facebook": "📘"
            }

            icon = icon_map.get(platform, "📁")
            avg_wait = data['avg_wait_per_request']

            lines.append(
                f"{icon} <b>{platform.title()}</b>\n"
                f"   Запросов: {data['request_count']}\n"
                f"   Интервал: {data['min_interval']}s\n"
                f"   Всего ожидания: {data['total_wait_time']:.1f}s\n"
                f"   Среднее ожидание: {avg_wait:.2f}s\n"
            )

        if len(lines) == 1:
            lines.append("Нет данных. Загрузки еще не было.")

        text = "\n".join(lines)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Сбросить статистику", callback_data="ratelimit_reset")]
        ])

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in ratelimit command: {e}")
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


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


@router.callback_query(lambda c: c.data.startswith("history_add_to_collection_"))
async def history_add_to_collection_callback(callback: CallbackQuery) -> None:
    """Добавить загрузку в коллекцию."""
    try:
        download_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        # Получаем коллекции пользователя
        collections = await db.get_collections(user_id)

        if not collections:
            await callback.answer(
                "❌ Сначала создайте коллекцию через /collections",
                show_alert=True
            )
            return

        # Показываем список коллекций для выбора
        buttons = []
        for collection in collections[:10]:
            buttons.append([InlineKeyboardButton(
                text=f"{collection['icon']} {collection['name']}",
                callback_data=f"add_to_col_{download_id}_{collection['id']}"
            )])

        buttons.append([InlineKeyboardButton(
            text="« Отмена",
            callback_data="show_history"
        )])

        text = "📁 <b>Выберите коллекцию:</b>"

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in add to collection: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("add_to_col_"))
async def add_to_col_callback(callback: CallbackQuery) -> None:
    """Подтвердить добавление в коллекцию."""
    try:
        parts = callback.data.split("_")
        download_id = int(parts[3])
        collection_id = int(parts[4])

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        success = await db.add_to_collection(download_id, collection_id)

        if success:
            await callback.answer("✅ Добавлено в коллекцию")
            await history_command(callback.message)
        else:
            await callback.answer("❌ Ошибка добавления", show_alert=True)

    except Exception as e:
        logger.error(f"Error confirming add to collection: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


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


# ==================== КОЛЛЕКЦИИ ====================

# Словарь для хранения состояний создания коллекции
collection_creation_state = {}


@router.callback_query(lambda c: c.data == "collection_create")
async def collection_create_callback(callback: CallbackQuery) -> None:
    """Начать создание коллекции."""
    user_id = callback.from_user.id

    text = (
        "📁 <b>Создание коллекции</b>\n\n"
        "Отправьте название для новой коллекции.\n\n"
        "Например: <code>Рецепты</code>, <code>Тренировки</code>, <code>Мотивация</code>\n\n"
        "💡 Можно добавить эмодзи в начале: 🍕 Рецепты"
    )

    # Устанавливаем состояние ожидания названия
    collection_creation_state[user_id] = {"waiting_for_name": True}

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("collection_open_"))
async def collection_open_callback(callback: CallbackQuery) -> None:
    """Открыть коллекцию."""
    try:
        collection_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        # Получаем элементы коллекции
        items = await db.get_collection_items(collection_id)

        # Получаем информацию о коллекции
        collections = await db.get_collections(user_id)
        collection = next((c for c in collections if c['id'] == collection_id), None)

        if not collection:
            await callback.answer("❌ Коллекция не найдена", show_alert=True)
            return

        if not items:
            text = (
                f"{collection['icon']} <b>{collection['name']}</b>\n\n"
                "Коллекция пуста.\n\n"
                "💡 Добавляйте загрузки в коллекцию через /history"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="« Назад к коллекциям", callback_data="back_to_collections")]
            ])
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback.answer()
            return

        platform_emoji = {
            "Instagram": "📸",
            "YouTube": "📺",
            "TikTok": "🎵",
            "VK": "🎬",
            "Twitter": "🐦",
            "X": "🐦"
        }

        # Формируем список элементов
        lines = []
        buttons = []

        for i, item in enumerate(items[:10], 1):
            emoji = platform_emoji.get(item['platform'], "📁")

            try:
                date = datetime.fromisoformat(item['download_date'])
                date_str = date.strftime("%d.%m")
            except:
                date_str = ""

            title = (item['title'] or "Без названия")[:30]
            if len(item['title'] or "") > 30:
                title += "..."

            lines.append(f"{i}. {emoji} {title} {date_str}")

            # Кнопки для первых 5
            if i <= 5:
                row = []
                row.append(InlineKeyboardButton(
                    text=f"{i}. Скачать",
                    callback_data=f"col_download_{item['id']}"
                ))
                row.append(InlineKeyboardButton(
                    text="🗑️",
                    callback_data=f"col_remove_{item['id']}_{collection_id}"
                ))
                buttons.append(row)

        buttons.append([InlineKeyboardButton(
            text="« Назад к коллекциям",
            callback_data="back_to_collections"
        )])

        text = (
            f"{collection['icon']} <b>{collection['name']}</b>\n\n" +
            "\n".join(lines)
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error opening collection: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("collection_delete_"))
async def collection_delete_callback(callback: CallbackQuery) -> None:
    """Удалить коллекцию."""
    try:
        collection_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        # Получаем информацию о коллекции для подтверждения
        collections = await db.get_collections(user_id)
        collection = next((c for c in collections if c['id'] == collection_id), None)

        if not collection:
            await callback.answer("❌ Коллекция не найдена", show_alert=True)
            return

        # Показываем подтверждение
        text = (
            f"🗑️ <b>Удалить коллекцию?</b>\n\n"
            f"{collection['icon']} {collection['name']}\n\n"
            "⚠️ Файлы из коллекции не будут удалены, только сама коллекция."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"collection_confirm_delete_{collection_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_collections")
            ]
        ])

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in delete collection: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("collection_confirm_delete_"))
async def collection_confirm_delete_callback(callback: CallbackQuery) -> None:
    """Подтвердить удаление коллекции."""
    try:
        collection_id = int(callback.data.split("_")[-1])

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        # Удаляем коллекцию (нужно добавить метод в db_manager)
        # Пока просто обнуляем collection_id у всех элементов
        items = await db.get_collection_items(collection_id)
        for item in items:
            await db.add_to_collection(item['id'], None)

        await callback.answer("✅ Коллекция удалена")
        await collections_command(callback.message)

    except Exception as e:
        logger.error(f"Error confirming delete: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("col_download_"))
async def col_download_callback(callback: CallbackQuery) -> None:
    """Скачать из коллекции."""
    try:
        download_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        item = await db.get_download_by_id(download_id)

        if not item or item['user_id'] != user_id:
            await callback.answer("❌ Элемент не найден", show_alert=True)
            return

        # Проверяем файл и отправляем
        file_path = item.get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                if file_path.endswith(('.mp4', '.mov', '.avi', '.webm')):
                    await callback.message.answer_video(
                        types.FSInputFile(file_path),
                        caption=f"📁 Из коллекции: {item['title'] or 'Видео'}"
                    )
                elif file_path.endswith(('.mp3', '.m4a', '.wav')):
                    await callback.message.answer_audio(
                        types.FSInputFile(file_path),
                        caption=f"📁 Из коллекции: {item['title'] or 'Аудио'}"
                    )
                elif file_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    await callback.message.answer_photo(
                        types.FSInputFile(file_path),
                        caption=f"📁 Из коллекции: {item['title'] or 'Фото'}"
                    )
                else:
                    await callback.message.answer_document(
                        types.FSInputFile(file_path),
                        caption=f"📁 Из коллекции: {item['title'] or 'Файл'}"
                    )
                await callback.answer("✅ Отправлено")
            except Exception as e:
                logger.error(f"Failed to resend: {e}")
                await callback.answer("⏳ Скачиваю заново...")
                await callback.message.answer(item['url'])
        else:
            await callback.answer("⏳ Скачиваю заново...")
            await callback.message.answer(item['url'])

    except Exception as e:
        logger.error(f"Error in col_download: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("col_remove_"))
async def col_remove_callback(callback: CallbackQuery) -> None:
    """Удалить из коллекции."""
    try:
        parts = callback.data.split("_")
        download_id = int(parts[2])
        collection_id = int(parts[3])

        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        # Убираем из коллекции
        await db.add_to_collection(download_id, None)

        await callback.answer("✅ Удалено из коллекции")

        # Обновляем список
        await collection_open_callback(
            CallbackQuery(
                id=callback.id,
                from_user=callback.from_user,
                message=callback.message,
                chat_instance=callback.chat_instance,
                data=f"collection_open_{collection_id}"
            )
        )

    except Exception as e:
        logger.error(f"Error in col_remove: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data == "back_to_collections")
async def back_to_collections_callback(callback: CallbackQuery) -> None:
    """Вернуться к списку коллекций."""
    await collections_command(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "ratelimit_reset")
async def ratelimit_reset_callback(callback: CallbackQuery) -> None:
    """Сбросить статистику rate limiter."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    rate_limiter.reset_stats()
    await callback.answer("✅ Статистика сброшена")
    await callback.message.answer("✅ Статистика rate limiter сброшена")


@router.message(Command("cleanup"))
async def cleanup_command(message: types.Message) -> None:
    """Управление автоматической очисткой файлов (admin only)."""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ Эта команда доступна только администратору")
        return

    logger.info(f"Admin {user_id} opened cleanup menu")

    from src.utils.file_cleaner import get_cleanup_service

    cleanup_service = get_cleanup_service()
    if not cleanup_service:
        await message.answer("❌ Сервис очистки не инициализирован")
        return

    try:
        stats = cleanup_service.get_stats()

        text = (
            "🗑️ <b>Автоматическая очистка файлов</b>\n\n"
            f"📊 <b>Статус:</b> {'✅ Запущен' if stats['is_running'] else '❌ Остановлен'}\n"
            f"⏱️ <b>Интервал:</b> каждые {stats['cleanup_interval_hours']} ч\n"
            f"🔄 <b>Циклов выполнено:</b> {stats['total_cleanup_runs']}\n"
            f"📁 <b>Файлов удалено:</b> {stats['total_files_deleted']}\n"
            f"💾 <b>Места освобождено:</b> {stats['total_space_freed_mb']:.2f} MB\n"
        )

        if stats['last_cleanup_time']:
            from datetime import datetime
            last_time = datetime.fromisoformat(stats['last_cleanup_time'])
            text += f"🕐 <b>Последняя очистка:</b> {last_time.strftime('%d.%m %H:%M')}\n"

        text += (
            "\n<b>Как работает:</b>\n"
            "• Проверяет настройку пользователя 'Авто-удаление'\n"
            "• Удаляет файлы старше указанного срока\n"
            "• Не удаляет избранные файлы (⭐)\n"
            "• Сохраняет записи в истории\n\n"
            "💡 Пользователи управляют сроком через /settings"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧹 Запустить вручную (все)",
                    callback_data="cleanup_manual_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Подробная статистика",
                    callback_data="cleanup_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="cleanup_refresh"
                )
            ]
        ])

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in cleanup command: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


@router.callback_query(lambda c: c.data == "cleanup_manual_all")
async def cleanup_manual_all_callback(callback: CallbackQuery) -> None:
    """Запустить ручную очистку для всех пользователей."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    from src.utils.file_cleaner import get_cleanup_service

    cleanup_service = get_cleanup_service()
    if not cleanup_service:
        await callback.answer("❌ Сервис недоступен", show_alert=True)
        return

    try:
        await callback.answer("⏳ Запускаю очистку...")

        # Показываем прогресс
        progress_msg = await callback.message.answer(
            "🧹 <b>Запуск ручной очистки...</b>\n\n"
            "⏳ Сканирую файлы пользователей...",
            parse_mode="HTML"
        )

        # Запускаем очистку
        result = await cleanup_service.manual_cleanup()

        if 'error' in result:
            await progress_msg.edit_text(
                f"❌ <b>Ошибка:</b>\n{result['error']}",
                parse_mode="HTML"
            )
            return

        # Показываем результат
        text = (
            "✅ <b>Очистка завершена!</b>\n\n"
            f"👥 <b>Пользователей обработано:</b> {result['users_cleaned']}\n"
            f"📁 <b>Файлов удалено:</b> {result['files_deleted']}\n"
            f"💾 <b>Места освобождено:</b> {result['space_freed_mb']:.2f} MB"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="cleanup_refresh")]
        ])

        await progress_msg.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in manual cleanup: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {safe_format_error(e, 50)}", show_alert=True)


@router.callback_query(lambda c: c.data == "cleanup_stats")
async def cleanup_stats_callback(callback: CallbackQuery) -> None:
    """Показать подробную статистику очистки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    from src.utils.file_cleaner import get_cleanup_service

    cleanup_service = get_cleanup_service()
    if not cleanup_service:
        await callback.answer("❌ Сервис недоступен", show_alert=True)
        return

    try:
        stats = cleanup_service.get_stats()

        text = (
            "📊 <b>Подробная статистика очистки</b>\n\n"
            f"🔄 <b>Всего циклов:</b> {stats['total_cleanup_runs']}\n"
            f"📁 <b>Всего файлов удалено:</b> {stats['total_files_deleted']}\n"
            f"💾 <b>Всего места освобождено:</b> {stats['total_space_freed_mb']:.2f} MB\n\n"
        )

        if stats['total_cleanup_runs'] > 0:
            avg_files = stats['total_files_deleted'] / stats['total_cleanup_runs']
            avg_space = stats['total_space_freed_mb'] / stats['total_cleanup_runs']
            text += (
                f"📈 <b>Среднее за цикл:</b>\n"
                f"• Файлов: {avg_files:.1f}\n"
                f"• Места: {avg_space:.2f} MB\n\n"
            )

        text += (
            f"⏱️ <b>Интервал:</b> {stats['cleanup_interval_hours']} часов\n"
            f"📊 <b>Статус:</b> {'✅ Активен' if stats['is_running'] else '❌ Остановлен'}\n"
        )

        if stats['last_cleanup_time']:
            from datetime import datetime
            last_time = datetime.fromisoformat(stats['last_cleanup_time'])
            text += f"\n🕐 <b>Последняя очистка:</b>\n{last_time.strftime('%d.%m.%Y %H:%M:%S')}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="cleanup_refresh")]
        ])

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in cleanup stats: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {safe_format_error(e, 50)}", show_alert=True)


@router.callback_query(lambda c: c.data == "cleanup_refresh")
async def cleanup_refresh_callback(callback: CallbackQuery) -> None:
    """Обновить информацию об очистке."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    # Вызываем основную команду заново
    await cleanup_command(callback.message)
    await callback.answer("✅ Обновлено")


@router.message(Command("export"))
async def export_command(message: types.Message) -> None:
    """Экспорт истории загрузок в CSV/JSON."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} opened export menu")

    try:
        db = get_db_manager()
        if not db:
            await message.answer("⚠️ Экспорт временно недоступен")
            return

        # Проверяем наличие истории
        history = await db.get_download_history(user_id, limit=1)
        if not history:
            await message.answer(
                "📂 <b>Экспорт истории</b>\n\n"
                "У вас пока нет загрузок для экспорта.\n"
                "Скачайте что-нибудь и попробуйте снова!",
                parse_mode="HTML"
            )
            return

        # Показываем меню выбора формата
        text = (
            "📤 <b>Экспорт истории загрузок</b>\n\n"
            "Выберите формат для экспорта:\n\n"
            "📊 <b>CSV</b> - табличный формат (Excel, Google Sheets)\n"
            "📋 <b>JSON</b> - структурированный формат (программирование)\n\n"
            "💡 Экспорт включает:\n"
            "• Дата и время загрузки\n"
            "• Платформа и тип контента\n"
            "• Название и автор\n"
            "• Ссылка на оригинал\n"
            "• Размер файла\n"
            "• Избранное"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 CSV (Excel)",
                    callback_data="export_csv_all"
                ),
                InlineKeyboardButton(
                    text="📋 JSON",
                    callback_data="export_json_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Только избранное (CSV)",
                    callback_data="export_csv_favorites"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Только избранное (JSON)",
                    callback_data="export_json_favorites"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 По платформам",
                    callback_data="export_by_platform"
                )
            ]
        ])

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in export command: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


@router.callback_query(lambda c: c.data.startswith("export_"))
async def export_callback(callback: CallbackQuery) -> None:
    """Обработать экспорт в выбранном формате."""
    user_id = callback.from_user.id
    data = callback.data

    try:
        db = get_db_manager()
        if not db:
            await callback.answer("❌ Недоступно", show_alert=True)
            return

        # Показываем прогресс
        await callback.answer("⏳ Готовлю экспорт...")

        progress_msg = await callback.message.answer(
            "📤 <b>Подготовка экспорта...</b>\n\n"
            "⏳ Загружаю данные из базы...",
            parse_mode="HTML"
        )

        # Определяем параметры экспорта
        format_type = 'csv' if 'csv' in data else 'json'
        favorites_only = 'favorites' in data
        platform = None

        # Специальная обработка для экспорта по платформам
        if data == "export_by_platform":
            # Показываем меню выбора платформы
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📸 Instagram", callback_data="export_platform_instagram"),
                    InlineKeyboardButton(text="📺 YouTube", callback_data="export_platform_youtube")
                ],
                [
                    InlineKeyboardButton(text="🎵 TikTok", callback_data="export_platform_tiktok"),
                    InlineKeyboardButton(text="🐦 Twitter", callback_data="export_platform_twitter")
                ],
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="export_back")
                ]
            ])

            await progress_msg.edit_text(
                "📊 <b>Выберите платформу для экспорта:</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return

        # Обработка экспорта по платформе
        if data.startswith("export_platform_"):
            platform = data.replace("export_platform_", "")
            format_type = 'csv'  # По умолчанию CSV для платформ

        # Выполняем экспорт
        content, stats = await export_user_history(
            db=db,
            user_id=user_id,
            format_type=format_type,
            platform=platform,
            favorites_only=favorites_only
        )

        # Обновляем прогресс
        await progress_msg.edit_text(
            "📤 <b>Создаю файл...</b>\n\n"
            f"📊 Записей: {stats['total_downloads']}\n"
            f"💾 Размер: {stats['total_size_mb']:.2f} MB",
            parse_mode="HTML"
        )

        # Сохраняем во временный файл
        exporter = HistoryExporter()
        filename = exporter.generate_filename(user_id, format_type)
        file_path = config.DATA_DIR / "exports" / filename

        if exporter.save_to_file(content, file_path):
            # Отправляем файл
            from aiogram.types import FSInputFile

            caption = (
                f"📤 <b>Экспорт истории загрузок</b>\n\n"
                f"📊 Всего записей: {stats['total_downloads']}\n"
                f"💾 Общий размер: {stats['total_size_mb']:.2f} MB\n"
            )

            if stats.get('favorites') and favorites_only:
                caption += f"⭐ Избранных: {stats['favorites']}\n"

            if platform:
                caption += f"📱 Платформа: {platform.capitalize()}\n"

            if stats.get('platforms'):
                caption += f"\n📈 По платформам:\n"
                for plat, count in stats['platforms'].items():
                    caption += f"  • {plat}: {count}\n"

            if stats.get('date_range'):
                dr = stats['date_range']
                caption += f"\n📅 Период: {dr['first']} — {dr['last']}"

            await callback.message.answer_document(
                document=FSInputFile(file_path),
                caption=caption,
                parse_mode="HTML"
            )

            # Удаляем прогресс-сообщение
            await progress_msg.delete()

            # Удаляем временный файл
            try:
                file_path.unlink()
            except Exception:
                pass

            logger.info(
                f"Exported history for user {user_id}: "
                f"{format_type}, {stats['total_downloads']} records"
            )

        else:
            await progress_msg.edit_text(
                "❌ <b>Ошибка создания файла</b>\n\n"
                "Попробуйте позже",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in export callback: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {safe_format_error(e, 50)}", show_alert=True)


@router.callback_query(lambda c: c.data == "export_back")
async def export_back_callback(callback: CallbackQuery) -> None:
    """Вернуться к меню экспорта."""
    await export_command(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "export_menu_from_history")
async def export_menu_from_history_callback(callback: CallbackQuery) -> None:
    """Открыть меню экспорта из истории."""
    await export_command(callback.message)
    await callback.answer()


@router.message(Command("search"))
async def search_command(message: types.Message) -> None:
    """Поиск по истории загрузок."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} opened search menu")

    try:
        db = get_db_manager()
        if not db:
            await message.answer("⚠️ Поиск временно недоступен")
            return

        # Проверяем наличие истории
        history = await db.get_download_history(user_id, limit=1)
        if not history:
            await message.answer(
                "🔍 <b>Поиск по истории</b>\n\n"
                "У вас пока нет загрузок для поиска.\n"
                "Скачайте что-нибудь и попробуйте снова!",
                parse_mode="HTML"
            )
            return

        # Получаем подсказки для поиска
        suggestions = await HistorySearcher.get_search_suggestions(user_id)

        text = (
            "🔍 <b>Поиск по истории загрузок</b>\n\n"
            f"📊 Всего загрузок: {suggestions.get('total_downloads', 0)}\n\n"
            "Выберите способ поиска или отправьте текст для поиска:"
        )

        # Кнопки быстрого поиска
        buttons = []

        # Поиск по платформам
        if suggestions.get('platforms'):
            buttons.append([InlineKeyboardButton(
                text="📱 По платформе",
                callback_data="search_by_platform"
            )])

        # Поиск по датам
        buttons.append([
            InlineKeyboardButton(
                text="📅 За последние 7 дней",
                callback_data="search_date_7"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="📅 За последний месяц",
                callback_data="search_date_30"
            )
        ])

        # Поиск по типу контента
        buttons.append([InlineKeyboardButton(
            text="🎬 По типу контента",
            callback_data="search_by_type"
        )])

        # Популярные авторы (если есть)
        if suggestions.get('authors'):
            buttons.append([InlineKeyboardButton(
                text="👤 По автору",
                callback_data="search_by_author"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        # Активируем режим поиска
        search_state[user_id] = {
            'active': True,
            'suggestions': suggestions
        }

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in search command: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {safe_format_error(e)}")


# Обработчик текстового поиска
@router.message(lambda msg: msg.from_user.id in search_state and
                search_state.get(msg.from_user.id, {}).get('active') and
                not msg.text.startswith('/'))
async def handle_search_query(message: types.Message) -> None:
    """Обработать текстовый поисковый запрос."""
    user_id = message.from_user.id
    query = message.text

    logger.info(f"User {user_id} searching: '{query}'")

    try:
        # Выполняем поиск
        progress_msg = await message.answer(
            f"🔍 Ищу \"{query}\"...",
            parse_mode="HTML"
        )

        results = await HistorySearcher.search(
            user_id=user_id,
            query=query,
            limit=50
        )

        # Форматируем результаты
        text = HistorySearcher.format_search_results(results, query)

        # Кнопки для результатов
        buttons = []

        if results:
            # Кнопки для первых результатов
            for i, item in enumerate(results[:5], 1):
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{i}. Скачать снова",
                        callback_data=f"history_redownload_{item['id']}"
                    ),
                    InlineKeyboardButton(
                        text="⭐" if not item.get('is_favorite') else "💔",
                        callback_data=f"history_{'favorite' if not item.get('is_favorite') else 'unfavorite'}_{item['id']}"
                    )
                ])

        # Кнопка новый поиск
        buttons.append([InlineKeyboardButton(
            text="🔍 Новый поиск",
            callback_data="search_new"
        )])

        # Кнопка экспорта результатов (если есть)
        if len(results) > 0:
            buttons.append([InlineKeyboardButton(
                text="📤 Экспортировать результаты",
                callback_data=f"search_export_{query}"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await progress_msg.delete()
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

        # Деактивируем режим поиска после результата
        search_state[user_id]['active'] = False

    except Exception as e:
        logger.error(f"Error in search query: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка поиска: {safe_format_error(e)}")


@router.callback_query(lambda c: c.data.startswith("search_"))
async def search_callback(callback: CallbackQuery) -> None:
    """Обработать callback для поиска."""
    user_id = callback.from_user.id
    data = callback.data

    try:
        # Новый поиск
        if data == "search_new":
            await search_command(callback.message)
            await callback.answer()
            return

        # Поиск по дате
        if data.startswith("search_date_"):
            days = int(data.replace("search_date_", ""))
            await callback.answer(f"⏳ Поиск за последние {days} дней...")

            results = await HistorySearcher.search_by_date_range(
                user_id=user_id,
                days=days,
                limit=50
            )

            text = HistorySearcher.format_search_results(
                results,
                query=f"Последние {days} дней"
            )

            buttons = []
            if results:
                for i, item in enumerate(results[:5], 1):
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"{i}. Скачать снова",
                            callback_data=f"history_redownload_{item['id']}"
                        )
                    ])

            buttons.append([InlineKeyboardButton(
                text="🔍 Новый поиск",
                callback_data="search_new"
            )])

            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            return

        # Поиск по платформе
        if data == "search_by_platform":
            # Показываем меню платформ
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📸 Instagram", callback_data="search_platform_instagram"),
                    InlineKeyboardButton(text="📺 YouTube", callback_data="search_platform_youtube")
                ],
                [
                    InlineKeyboardButton(text="🎵 TikTok", callback_data="search_platform_tiktok"),
                    InlineKeyboardButton(text="🐦 Twitter", callback_data="search_platform_twitter")
                ],
                [
                    InlineKeyboardButton(text="🎬 VK", callback_data="search_platform_vk")
                ],
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="search_new")
                ]
            ])

            await callback.message.edit_text(
                "📱 <b>Выберите платформу:</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await callback.answer()
            return

        # Поиск конкретной платформы
        if data.startswith("search_platform_"):
            platform = data.replace("search_platform_", "")
            await callback.answer(f"⏳ Ищу в {platform.capitalize()}...")

            results = await HistorySearcher.search(
                user_id=user_id,
                platform=platform,
                limit=50
            )

            text = HistorySearcher.format_search_results(
                results,
                query=f"Платформа: {platform.capitalize()}"
            )

            buttons = []
            if results:
                for i, item in enumerate(results[:5], 1):
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"{i}. Скачать снова",
                            callback_data=f"history_redownload_{item['id']}"
                        )
                    ])

            buttons.append([InlineKeyboardButton(
                text="🔍 Новый поиск",
                callback_data="search_new"
            )])

            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            return

        # Поиск по типу контента
        if data == "search_by_type":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎬 Видео", callback_data="search_type_video"),
                    InlineKeyboardButton(text="📷 Фото", callback_data="search_type_photo")
                ],
                [
                    InlineKeyboardButton(text="🎵 Аудио", callback_data="search_type_audio"),
                    InlineKeyboardButton(text="📸 Карусель", callback_data="search_type_carousel")
                ],
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="search_new")
                ]
            ])

            await callback.message.edit_text(
                "🎬 <b>Выберите тип контента:</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await callback.answer()
            return

        # Поиск конкретного типа
        if data.startswith("search_type_"):
            content_type = data.replace("search_type_", "")
            await callback.answer(f"⏳ Ищу {content_type}...")

            results = await HistorySearcher.search(
                user_id=user_id,
                content_type=content_type,
                limit=50
            )

            text = HistorySearcher.format_search_results(
                results,
                query=f"Тип: {content_type.capitalize()}"
            )

            buttons = []
            if results:
                for i, item in enumerate(results[:5], 1):
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"{i}. Скачать снова",
                            callback_data=f"history_redownload_{item['id']}"
                        )
                    ])

            buttons.append([InlineKeyboardButton(
                text="🔍 Новый поиск",
                callback_data="search_new"
            )])

            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            return

    except Exception as e:
        logger.error(f"Error in search callback: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {safe_format_error(e, 50)}", show_alert=True)


@router.callback_query(lambda c: c.data == "open_search")
async def open_search_callback(callback: CallbackQuery) -> None:
    """Открыть поиск из истории."""
    await search_command(callback.message)
    await callback.answer()
