"""
URL Processor - определение платформы и извлечение идентификаторов
"""
import re
from typing import Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Platform(str, Enum):
    """Поддерживаемые платформы"""
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    VK = "vk"
    X = "x"
    UNKNOWN = "unknown"


@dataclass
class URLInfo:
    """Информация об извлеченной ссылке"""
    platform: Platform
    url: str
    post_id: Optional[str] = None
    username: Optional[str] = None
    content_type: Optional[str] = None  # video, photo, story, reel, shorts
    is_valid: bool = True
    error_message: Optional[str] = None


class URLProcessor:
    """Обработчик URL для определения платформы и валидации"""

    # Регулярные выражения для каждой платформы
    INSTAGRAM_PATTERNS = [
        r"https?://(?:www\.)?instagram\.com/(?:p|reel)/([a-zA-Z0-9_-]+)",  # post/reel
        r"https?://(?:www\.)?instagram\.com/stories/([^/?]+)/(\d+)",  # stories
        r"https?://(?:www\.)?instagram\.com/(?:p|reel)/([a-zA-Z0-9_-]+)/",
    ]

    YOUTUBE_PATTERNS = [
        r"https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",  # long URL
        r"https?://youtu\.be/([a-zA-Z0-9_-]+)",  # short URL
        r"https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)",  # shorts
    ]

    TIKTOK_PATTERNS = [
        r"https?://(?:www\.)?tiktok\.com/@([^/]+)/video/(\d+)",  # full URL
        r"https?://vm\.tiktok\.com/([a-zA-Z0-9]+)",  # short URL
        r"https?://vt\.tiktok\.com/([a-zA-Z0-9]+)",  # another short URL
    ]

    VK_PATTERNS = [
        r"https?://(?:www\.)?vk\.com/(?:wall|video|audio|photo)(-?\d+_\d+)",  # wall/video/audio/photo posts
        r"https?://(?:www\.)?vk\.com/video(-?\d+_\d+)",  # video
        r"https?://(?:www\.)?vk\.com/wall(-?\d+)\?.*",  # wall posts
        r"https?://vk\.com/(?:wall|video)(-?\d+_\d+)",  # short formats
        r"https?://(?:www\.)?vk\.com/video_ext\.php\?.*",  # embedded video (handled separately)
        r"https?://(?:www\.)?vkvideo\.ru/.*video(-?\d+_\d+)",  # vkvideo.ru
    ]

    X_PATTERNS = [
        r"https?://(?:www\.)?(?:twitter|x)\.com/\w+/status/(\d+)",  # tweets
        r"https?://(?:www\.)?x\.com/\w+/(?:status|web)/?(\d+)",  # x.com tweets
        r"https?://(?:twitter\.com)/\w+/status/(\d+)",  # twitter.com tweets
    ]

    @staticmethod
    def detect_platform(url: str) -> Platform:
        """Определяет платформу по URL"""
        if not url:
            return Platform.UNKNOWN

        url_lower = url.lower()

        if "instagram.com" in url_lower:
            return Platform.INSTAGRAM
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return Platform.YOUTUBE
        elif "tiktok.com" in url_lower or "vm.tiktok.com" in url_lower or "vt.tiktok.com" in url_lower:
            return Platform.TIKTOK
        elif "vk.com" in url_lower or "vkontakte.com" in url_lower or "vkvideo.ru" in url_lower:
            return Platform.VK
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return Platform.X

        return Platform.UNKNOWN

    @staticmethod
    def extract_instagram_id(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлекает ID и тип контента из Instagram URL"""
        for pattern in URLProcessor.INSTAGRAM_PATTERNS:
            match = re.search(pattern, url)
            if match:
                # Определяем тип контента
                if "/stories/" in url:
                    content_type = "story"
                elif "/reel/" in url:
                    content_type = "reel"
                else:
                    content_type = "photo"

                post_id = match.group(1)
                return post_id, content_type

        return None, None

    @staticmethod
    def extract_youtube_id(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлекает ID и тип видео из YouTube URL"""
        for pattern in URLProcessor.YOUTUBE_PATTERNS:
            match = re.search(pattern, url)
            if match:
                # Определяем тип контента
                if "/shorts/" in url:
                    content_type = "shorts"
                else:
                    content_type = "video"

                video_id = match.group(1)
                return video_id, content_type

        return None, None

    @staticmethod
    def extract_tiktok_id(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлекает ID из TikTok URL"""
        # Для полного URL
        full_pattern = r"https?://(?:www\.)?tiktok\.com/@([^/]+)/video/(\d+)"
        match = re.search(full_pattern, url)
        if match:
            username = match.group(1)
            video_id = match.group(2)
            return video_id, "video"

        # Для коротких URL
        short_patterns = [
            r"https?://vm\.tiktok\.com/([a-zA-Z0-9]+)",
            r"https?://vt\.tiktok\.com/([a-zA-Z0-9]+)",
        ]
        for pattern in short_patterns:
            match = re.search(pattern, url)
            if match:
                short_id = match.group(1)
                return short_id, "video"

        return None, None

    @staticmethod
    def extract_vk_id(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлекает ID из VK URL"""
        from urllib.parse import urlparse, parse_qs

        # Специальная обработка video_ext.php (embedded video)
        if "video_ext.php" in url:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                oid = params.get("oid", [None])[0]
                vid = params.get("id", [None])[0]
                if oid and vid:
                    post_id = f"{oid}_{vid}"
                    return post_id, "video"
            except Exception:
                pass

        for pattern in URLProcessor.VK_PATTERNS:
            match = re.search(pattern, url)
            if match:
                post_id = match.group(1)

                # Определяем тип контента
                if "/video" in url:
                    content_type = "video"
                elif "/audio" in url:
                    content_type = "audio"
                elif "/photo" in url:
                    content_type = "photo"
                else:
                    content_type = "post"

                return post_id, content_type

        return None, None

    @staticmethod
    def extract_x_id(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлекает ID твита из X/Twitter URL"""
        for pattern in URLProcessor.X_PATTERNS:
            match = re.search(pattern, url)
            if match:
                tweet_id = match.group(1)
                return tweet_id, "tweet"

        return None, None

    def process(self, url: str) -> URLInfo:
        """
        Главный метод обработки URL
        Возвращает объект URLInfo с информацией о найденной ссылке
        """
        if not url:
            return URLInfo(
                platform=Platform.UNKNOWN,
                url=url,
                is_valid=False,
                error_message="URL не может быть пустым",
            )

        # Удаляем пробелы
        url = url.strip()

        # Проверяем, что это URL
        if not url.startswith(("http://", "https://")):
            return URLInfo(
                platform=Platform.UNKNOWN,
                url=url,
                is_valid=False,
                error_message="Ссылка должна начинаться с http:// или https://",
            )

        platform = self.detect_platform(url)

        if platform == Platform.INSTAGRAM:
            post_id, content_type = self.extract_instagram_id(url)
            return URLInfo(
                platform=platform,
                url=url,
                post_id=post_id,
                content_type=content_type,
                is_valid=post_id is not None,
                error_message=None if post_id else "Не удалось извлечь ID поста",
            )

        elif platform == Platform.YOUTUBE:
            video_id, content_type = self.extract_youtube_id(url)
            return URLInfo(
                platform=platform,
                url=url,
                post_id=video_id,
                content_type=content_type,
                is_valid=video_id is not None,
                error_message=None if video_id else "Не удалось извлечь ID видео",
            )

        elif platform == Platform.TIKTOK:
            video_id, content_type = self.extract_tiktok_id(url)
            return URLInfo(
                platform=platform,
                url=url,
                post_id=video_id,
                content_type=content_type,
                is_valid=video_id is not None,
                error_message=None if video_id else "Не удалось извлечь ID видео",
            )

        elif platform == Platform.VK:
            post_id, content_type = self.extract_vk_id(url)
            # Нормализуем URL для yt-dlp (video_ext.php, vkvideo.ru -> vk.com/video)
            normalized_url = url
            if post_id and content_type == "video":
                if "video_ext.php" in url or "vkvideo.ru" in url:
                    normalized_url = f"https://vk.com/video{post_id}"
            return URLInfo(
                platform=platform,
                url=normalized_url,
                post_id=post_id,
                content_type=content_type,
                is_valid=post_id is not None,
                error_message=None if post_id else "Не удалось извлечь ID поста VK",
            )

        elif platform == Platform.X:
            tweet_id, content_type = self.extract_x_id(url)
            return URLInfo(
                platform=platform,
                url=url,
                post_id=tweet_id,
                content_type=content_type,
                is_valid=tweet_id is not None,
                error_message=None if tweet_id else "Не удалось извлечь ID твита",
            )

        else:
            return URLInfo(
                platform=Platform.UNKNOWN,
                url=url,
                is_valid=False,
                error_message="Неподдерживаемая платформа. Поддерживаем: Instagram, YouTube, TikTok, VK, X",
            )


def extract_urls_from_text(text: str) -> list:
    """Извлекает все URL из текста"""
    url_pattern = r"https?://[^\s]+"
    urls = re.findall(url_pattern, text)
    return urls
