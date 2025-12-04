"""
Media Downloader - загрузка медиа со всех платформ
Использует yt-dlp для универсальной загрузки видео, аудио, фото
"""
import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from src.utils.logger import get_logger
from src.config import config

logger = get_logger(__name__)


@dataclass
class DownloadInfo:
    """Информация о скачанном файле"""
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    duration: Optional[float] = None  # для видео/аудио в секундах
    title: Optional[str] = None
    error_message: Optional[str] = None
    platform: Optional[str] = None


class MediaDownloader:
    """Загрузчик медиа со всех платформ"""

    # Директории для разных типов контента
    DOWNLOAD_DIRS = {
        "video": config.DATA_DIR / "videos",
        "audio": config.DATA_DIR / "audio",
        "photo": config.DATA_DIR / "photos",
        "other": config.DATA_DIR / "other",
    }

    # Максимальные размеры файлов (в байтах)
    MAX_FILE_SIZES = {
        "video": 100 * 1024 * 1024,  # 100 MB
        "audio": 50 * 1024 * 1024,   # 50 MB
        "photo": 10 * 1024 * 1024,   # 10 MB
    }

    # Параметры yt-dlp для разных платформ
    YDL_OPTS_BASE = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "socket_timeout": 30,
    }

    YDL_OPTS_VIDEO = {
        **YDL_OPTS_BASE,
        "format": "best[ext=mp4]/best",
        "postprocessors": [],
    }

    YDL_OPTS_AUDIO = {
        **YDL_OPTS_BASE,
        "format": "bestaudio",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    def __init__(self):
        """Инициализация downloader'а"""
        self._ensure_directories()

    @classmethod
    def _ensure_directories(cls):
        """Создает необходимые директории"""
        for dir_path in cls.DOWNLOAD_DIRS.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {dir_path}")

    def _get_download_path(self, content_type: str, filename: str) -> Path:
        """Получает полный путь для загрузки"""
        dir_key = content_type if content_type in self.DOWNLOAD_DIRS else "other"
        return self.DOWNLOAD_DIRS[dir_key] / filename

    def _check_file_size(self, file_path: Path, content_type: str) -> bool:
        """Проверяет размер файла"""
        if not file_path.exists():
            return False

        max_size = self.MAX_FILE_SIZES.get(content_type, 50 * 1024 * 1024)
        file_size = file_path.stat().st_size

        if file_size > max_size:
            logger.warning(
                f"File size {file_size} exceeds max {max_size} for {content_type}"
            )
            file_path.unlink()  # Удаляем файл
            return False

        return True

    async def download_video(
        self, url: str, platform: str = "unknown"
    ) -> DownloadInfo:
        """
        Загружает видео с URL
        Поддерживает: YouTube, Instagram, TikTok, Twitter/X, VK
        """
        try:
            logger.info(f"Starting video download from {platform}: {url}")

            try:
                import yt_dlp
            except ImportError:
                return DownloadInfo(
                    success=False,
                    platform=platform,
                    error_message="yt-dlp не установлен. Установите: pip install yt-dlp",
                )

            output_template = str(
                self.DOWNLOAD_DIRS["video"] / "%(title)s.%(ext)s"
            )

            ydl_opts = self.YDL_OPTS_VIDEO.copy()
            ydl_opts["outtmpl"] = output_template

            # Специальные опции для разных платформ
            if platform.lower() == "instagram":
                ydl_opts["format"] = "best"
                ydl_opts["postprocessors"] = []
            elif platform.lower() == "tiktok":
                ydl_opts["format"] = "best[ext=mp4]/best"
            elif platform.lower() == "vk":
                ydl_opts["format"] = "best"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Запускаем в отдельном процессе чтобы не блокировать бот
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, ydl.extract_info, url, False)

            if not info:
                return DownloadInfo(
                    success=False,
                    platform=platform,
                    error_message="Не удалось извлечь информацию о видео",
                )

            title = info.get("title", "Unknown")
            filename = info.get("_filename", "")

            if filename and os.path.exists(filename):
                # Проверяем размер
                if self._check_file_size(Path(filename), "video"):
                    file_size = os.path.getsize(filename)
                    duration = info.get("duration")

                    logger.info(
                        f"Video downloaded successfully: {title} ({file_size} bytes)"
                    )

                    return DownloadInfo(
                        success=True,
                        file_path=filename,
                        file_size=file_size,
                        duration=duration,
                        title=title,
                        platform=platform,
                    )
                else:
                    return DownloadInfo(
                        success=False,
                        platform=platform,
                        error_message=f"Видео слишком большое (максимум 100 MB)",
                    )
            else:
                return DownloadInfo(
                    success=False,
                    platform=platform,
                    error_message="Видео загружено но файл не найден",
                )

        except Exception as e:
            logger.error(f"Error downloading video from {platform}: {str(e)}")
            return DownloadInfo(
                success=False,
                platform=platform,
                error_message=f"Ошибка загрузки: {str(e)[:100]}",
            )

    async def download_audio(
        self, url: str, platform: str = "unknown"
    ) -> DownloadInfo:
        """Загружает аудио (используется для VK аудио)"""
        try:
            logger.info(f"Starting audio download from {platform}: {url}")

            try:
                import yt_dlp
            except ImportError:
                return DownloadInfo(
                    success=False,
                    platform=platform,
                    error_message="yt-dlp не установлен",
                )

            output_template = str(
                self.DOWNLOAD_DIRS["audio"] / "%(title)s.%(ext)s"
            )

            ydl_opts = self.YDL_OPTS_AUDIO.copy()
            ydl_opts["outtmpl"] = output_template

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, ydl.extract_info, url, False)

            if info and "_filename" in info:
                filename = info.get("_filename", "")
                if os.path.exists(filename):
                    if self._check_file_size(Path(filename), "audio"):
                        file_size = os.path.getsize(filename)
                        title = info.get("title", "Unknown")

                        logger.info(f"Audio downloaded: {title}")

                        return DownloadInfo(
                            success=True,
                            file_path=filename,
                            file_size=file_size,
                            title=title,
                            platform=platform,
                        )

            return DownloadInfo(
                success=False,
                platform=platform,
                error_message="Не удалось загрузить аудио",
            )

        except Exception as e:
            logger.error(f"Error downloading audio from {platform}: {str(e)}")
            return DownloadInfo(
                success=False,
                platform=platform,
                error_message=f"Ошибка: {str(e)[:100]}",
            )

    async def download_photo(
        self, url: str, platform: str = "unknown"
    ) -> DownloadInfo:
        """Загружает фото"""
        try:
            logger.info(f"Starting photo download from {platform}: {url}")

            try:
                import yt_dlp
            except ImportError:
                return DownloadInfo(
                    success=False,
                    platform=platform,
                    error_message="yt-dlp не установлен",
                )

            output_template = str(
                self.DOWNLOAD_DIRS["photo"] / "%(title)s.%(ext)s"
            )

            ydl_opts = self.YDL_OPTS_BASE.copy()
            ydl_opts["outtmpl"] = output_template
            ydl_opts["format"] = "best"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, ydl.extract_info, url, False)

            if info and "_filename" in info:
                filename = info.get("_filename", "")
                if os.path.exists(filename):
                    if self._check_file_size(Path(filename), "photo"):
                        file_size = os.path.getsize(filename)
                        title = info.get("title", "Unknown")

                        logger.info(f"Photo downloaded: {title}")

                        return DownloadInfo(
                            success=True,
                            file_path=filename,
                            file_size=file_size,
                            title=title,
                            platform=platform,
                        )

            return DownloadInfo(
                success=False,
                platform=platform,
                error_message="Не удалось загрузить фото",
            )

        except Exception as e:
            logger.error(f"Error downloading photo from {platform}: {str(e)}")
            return DownloadInfo(
                success=False,
                platform=platform,
                error_message=f"Ошибка: {str(e)[:100]}",
            )

    async def download(
        self, url: str, content_type: str = "video", platform: str = "unknown"
    ) -> DownloadInfo:
        """
        Универсальный метод загрузки
        Определяет тип контента и загружает соответствующим образом
        """
        if content_type == "audio":
            return await self.download_audio(url, platform)
        elif content_type == "photo":
            return await self.download_photo(url, platform)
        else:
            # По умолчанию видео
            return await self.download_video(url, platform)

    def cleanup_old_files(self, days: int = 7):
        """Очищает старые скачанные файлы"""
        import time

        try:
            current_time = time.time()
            threshold = current_time - (days * 24 * 60 * 60)

            for dir_path in self.DOWNLOAD_DIRS.values():
                if not dir_path.exists():
                    continue

                for file_path in dir_path.glob("*"):
                    if file_path.is_file():
                        if file_path.stat().st_mtime < threshold:
                            file_path.unlink()
                            logger.debug(f"Deleted old file: {file_path}")

        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")
