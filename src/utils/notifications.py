"""
Модуль уведомлений в супергруппу админов с топиками для каждого пользователя
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Супергруппа для уведомлений (из URL https://t.me/c/3307715316/ извлекаем ID)
# Формат: -100 + ID группы
SUPERGROUP_ID = int(os.getenv("ADMIN_SUPERGROUP_ID", "-1003307715316"))

# Файл для хранения маппинга user_id -> topic_id
TOPICS_CACHE_FILE = Path("/opt/uspsocdowloader/data/cache/user_topics.json")


class NotificationManager:
    """Менеджер уведомлений в супергруппу с топиками"""

    def __init__(self, bot: Bot = None):
        self.bot = bot
        self.enabled = bool(SUPERGROUP_ID)
        self.user_topics: Dict[int, int] = {}  # user_id -> topic_id
        self._load_topics_cache()

    def _load_topics_cache(self):
        """Загружает кэш топиков из файла"""
        try:
            if TOPICS_CACHE_FILE.exists():
                with open(TOPICS_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    # Конвертируем ключи обратно в int
                    self.user_topics = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded {len(self.user_topics)} user topics from cache")
        except Exception as e:
            logger.error(f"Error loading topics cache: {e}")
            self.user_topics = {}

    def _save_topics_cache(self):
        """Сохраняет кэш топиков в файл"""
        try:
            TOPICS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TOPICS_CACHE_FILE, 'w') as f:
                json.dump(self.user_topics, f)
        except Exception as e:
            logger.error(f"Error saving topics cache: {e}")

    def set_bot(self, bot: Bot):
        """Устанавливает экземпляр бота"""
        self.bot = bot

    async def get_or_create_user_topic(self, user_id: int, username: str = None,
                                        first_name: str = None) -> Optional[int]:
        """Получает или создаёт топик для пользователя"""
        if not self.bot or not self.enabled:
            return None

        # Проверяем кэш
        if user_id in self.user_topics:
            return self.user_topics[user_id]

        # Формируем название топика
        if username:
            topic_name = f"@{username}"
        elif first_name:
            topic_name = f"{first_name} ({user_id})"
        else:
            topic_name = str(user_id)

        try:
            # Создаём новый топик
            result = await self.bot.create_forum_topic(
                chat_id=SUPERGROUP_ID,
                name=topic_name[:128],  # Максимум 128 символов
                icon_custom_emoji_id=None  # Можно добавить кастомный эмодзи
            )

            topic_id = result.message_thread_id
            self.user_topics[user_id] = topic_id
            self._save_topics_cache()

            logger.info(f"Created topic '{topic_name}' (id: {topic_id}) for user {user_id}")
            return topic_id

        except TelegramBadRequest as e:
            if "TOPIC_ALREADY_EXISTS" in str(e):
                logger.warning(f"Topic for user {user_id} might already exist")
            else:
                logger.error(f"Failed to create topic for user {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating topic for user {user_id}: {e}")
            return None

    async def send_notification(self, message: str, user_id: int = None,
                                username: str = None, first_name: str = None,
                                parse_mode: str = "HTML") -> bool:
        """Отправляет уведомление в топик пользователя или общий чат"""
        if not self.enabled or not self.bot:
            return False

        try:
            message_thread_id = None

            # Если указан user_id, пытаемся отправить в его топик
            if user_id:
                message_thread_id = await self.get_or_create_user_topic(
                    user_id, username, first_name
                )

            await self.bot.send_message(
                chat_id=SUPERGROUP_ID,
                text=message,
                parse_mode=parse_mode,
                message_thread_id=message_thread_id
            )
            return True

        except TelegramBadRequest as e:
            # Если топик был удалён, удаляем из кэша и пробуем создать заново
            if "message thread not found" in str(e).lower() and user_id:
                logger.warning(f"Topic for user {user_id} not found, recreating...")
                self.user_topics.pop(user_id, None)
                self._save_topics_cache()

                # Пробуем создать заново
                message_thread_id = await self.get_or_create_user_topic(
                    user_id, username, first_name
                )
                if message_thread_id:
                    try:
                        await self.bot.send_message(
                            chat_id=SUPERGROUP_ID,
                            text=message,
                            parse_mode=parse_mode,
                            message_thread_id=message_thread_id
                        )
                        return True
                    except:
                        pass

            logger.error(f"Failed to send notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send notification to supergroup: {e}")
            return False

    async def notify_new_user(self, user_id: int, username: str = None,
                             first_name: str = None, last_name: str = None,
                             is_premium: bool = False, referrer_id: int = None) -> bool:
        """Уведомление о новом пользователе"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        name_parts = []
        if first_name:
            name_parts.append(first_name)
        if last_name:
            name_parts.append(last_name)
        full_name = " ".join(name_parts) or "Unknown"

        premium_badge = "⭐ " if is_premium else ""
        referrer_info = f"\n👤 Реферер: <code>{referrer_id}</code>" if referrer_id else ""

        message = f"""🆕 <b>Новый пользователь</b>

{premium_badge}👤 <b>{full_name}</b>
🆔 ID: <code>{user_id}</code>
📛 Username: @{username if username else 'нет'}
🕐 Время: {now}{referrer_info}"""

        return await self.send_notification(message, user_id, username, first_name)

    async def notify_download_request(self, user_id: int, username: str,
                                      platform: str, url: str,
                                      content_type: str = None) -> bool:
        """Уведомление о запросе на скачивание"""
        now = datetime.now().strftime("%H:%M:%S")

        platform_emoji = {
            "instagram": "📷",
            "youtube": "🎥",
            "tiktok": "🎵",
            "twitter": "𝕏",
            "vk": "🔵"
        }.get(platform.lower(), "🔗")

        # Сокращаем URL для отображения
        short_url = url[:80] + "..." if len(url) > 80 else url

        message = f"""{platform_emoji} <b>{platform}</b> | {content_type or "media"}

🔗 <code>{short_url}</code>
🕐 {now}"""

        return await self.send_notification(message, user_id, username)

    async def notify_download_success(self, user_id: int, username: str,
                                      platform: str, file_size_mb: float,
                                      duration: float = None,
                                      ai_used: str = None) -> bool:
        """Уведомление об успешном скачивании"""
        now = datetime.now().strftime("%H:%M:%S")

        duration_info = f" ⏱️ {int(duration//60)}:{int(duration%60):02d}" if duration else ""
        ai_info = f"\n🤖 AI: {ai_used}" if ai_used else ""

        message = f"""✅ <b>Успешно</b> | {platform}

📊 {file_size_mb:.1f} MB{duration_info}{ai_info}
🕐 {now}"""

        return await self.send_notification(message, user_id, username)

    async def notify_download_error(self, user_id: int, username: str,
                                   platform: str, error: str, url: str = None) -> bool:
        """Уведомление об ошибке скачивания"""
        now = datetime.now().strftime("%H:%M:%S")

        url_info = f"\n🔗 <code>{url[:60]}...</code>" if url and len(url) > 60 else (f"\n🔗 <code>{url}</code>" if url else "")

        message = f"""❌ <b>Ошибка</b> | {platform}
{url_info}
⚠️ {error[:150]}
🕐 {now}"""

        return await self.send_notification(message, user_id, username)

    async def notify_ai_usage(self, user_id: int, username: str,
                             ai_type: str, text_length: int) -> bool:
        """Уведомление об использовании AI"""
        now = datetime.now().strftime("%H:%M:%S")

        ai_emoji = {
            "translate": "🌐",
            "rewrite": "✍️",
            "ocr": "📷"
        }.get(ai_type, "🤖")

        ai_name = {
            "translate": "Перевод",
            "rewrite": "Рерайт",
            "ocr": "OCR"
        }.get(ai_type, ai_type)

        message = f"""{ai_emoji} <b>AI: {ai_name}</b>

📝 {text_length} символов
🕐 {now}"""

        return await self.send_notification(message, user_id, username)

    async def notify_daily_stats(self, total_users: int, new_users: int,
                                total_requests: int, successful: int,
                                failed: int, total_mb: float) -> bool:
        """Ежедневная статистика (в общий чат без топика)"""
        today = datetime.now().strftime("%Y-%m-%d")

        success_rate = (successful / total_requests * 100) if total_requests > 0 else 0

        message = f"""📊 <b>Статистика за {today}</b>

👥 Всего пользователей: {total_users}
🆕 Новых: {new_users}

📥 Запросов: {total_requests}
✅ Успешных: {successful} ({success_rate:.1f}%)
❌ Ошибок: {failed}

📦 Скачано: {total_mb:.1f} MB"""

        # Отправляем без user_id - в общий чат
        return await self.send_notification(message)


# Singleton instance
notification_manager = NotificationManager()
