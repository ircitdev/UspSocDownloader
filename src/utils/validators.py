"""
Валидаторы для URL и контента
"""
import re
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class URLValidator:
    """Валидация URL"""

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Проверяет валидность базовой структуры URL"""
        if not url or not isinstance(url, str):
            return False

        url_pattern = r"^https?://[^\s]+"
        return bool(re.match(url_pattern, url))

    @staticmethod
    def is_instagram_url(url: str) -> bool:
        """Проверяет является ли URL Instagram ссылкой"""
        return bool(re.search(r"instagram\.com", url, re.IGNORECASE))

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Проверяет является ли URL YouTube ссылкой"""
        return bool(re.search(r"youtube\.com|youtu\.be", url, re.IGNORECASE))

    @staticmethod
    def is_tiktok_url(url: str) -> bool:
        """Проверяет является ли URL TikTok ссылкой"""
        return bool(re.search(r"tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com", url, re.IGNORECASE))

    @staticmethod
    def is_vk_url(url: str) -> bool:
        """Проверяет является ли URL VK ссылкой"""
        return bool(re.search(r"vk\.com|vkontakte\.com", url, re.IGNORECASE))

    @staticmethod
    def is_x_url(url: str) -> bool:
        """Проверяет является ли URL X/Twitter ссылкой"""
        return bool(re.search(r"twitter\.com|x\.com", url, re.IGNORECASE))

    @staticmethod
    def is_supported_platform(url: str) -> bool:
        """Проверяет поддерживается ли платформа"""
        return (
            URLValidator.is_instagram_url(url)
            or URLValidator.is_youtube_url(url)
            or URLValidator.is_tiktok_url(url)
            or URLValidator.is_vk_url(url)
            or URLValidator.is_x_url(url)
        )


class MessageValidator:
    """Валидация сообщений"""

    MAX_URL_LENGTH = 2048
    MAX_MESSAGE_LENGTH = 4096

    @staticmethod
    def is_valid_message(text: str) -> bool:
        """Проверяет валидность сообщения"""
        if not text or not isinstance(text, str):
            return False

        if len(text) > MessageValidator.MAX_MESSAGE_LENGTH:
            return False

        return True

    @staticmethod
    def contains_url(text: str) -> bool:
        """Проверяет содержит ли сообщение URL"""
        url_pattern = r"https?://[^\s]+"
        return bool(re.search(url_pattern, text))

    @staticmethod
    def extract_urls(text: str) -> list:
        """Извлекает все URL из сообщения"""
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, text)
        return [url for url in urls if len(url) <= MessageValidator.MAX_URL_LENGTH]

    @staticmethod
    def validate_and_extract_urls(text: str) -> tuple:
        """
        Валидирует сообщение и извлекает URL
        Возвращает (is_valid, urls, error_message)
        """
        if not MessageValidator.is_valid_message(text):
            return False, [], "Некорректное сообщение"

        if not MessageValidator.contains_url(text):
            return False, [], "Сообщение не содержит URL"

        urls = MessageValidator.extract_urls(text)
        if not urls:
            return False, [], "Не удалось извлечь URL"

        return True, urls, None
