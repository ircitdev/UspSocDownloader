"""
Media Downloader - загрузка медиа со всех платформ
Использует yt-dlp для универсальной загрузки видео, аудио, фото
"""
import os
import asyncio
import random
import time
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
    file_paths: Optional[List[str]] = None  # Для карусели - несколько файлов
    file_size: int = 0
    duration: Optional[float] = None
    title: Optional[str] = None
    description: Optional[str] = None  # Описание/текст поста
    author: Optional[str] = None  # Автор (username)
    author_name: Optional[str] = None  # Имя автора
    likes: Optional[int] = None
    comments: Optional[int] = None
    views: Optional[int] = None
    url: Optional[str] = None  # Ссылка на пост
    error_message: Optional[str] = None
    platform: Optional[str] = None
    is_carousel: bool = False  # Карусель из нескольких медиа


class MediaDownloader:
    """Загрузчик медиа со всех платформ"""

    DOWNLOAD_DIRS = {
        "video": config.DATA_DIR / "videos",
        "audio": config.DATA_DIR / "audio",
        "photo": config.DATA_DIR / "photos",
        "other": config.DATA_DIR / "other",
    }

    MAX_FILE_SIZES = {
        "video": 100 * 1024 * 1024,
        "audio": 50 * 1024 * 1024,
        "photo": 10 * 1024 * 1024,
    }

    # User agents для обхода блокировок
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    ]

    YDL_OPTS_BASE = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "socket_timeout": 60,
        "retries": 5,
        "fragment_retries": 5,
        "ignoreerrors": False,
        "nocheckcertificate": True,
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
        self._ensure_directories()

    @classmethod
    def _ensure_directories(cls):
        for dir_path in cls.DOWNLOAD_DIRS.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    def _get_random_user_agent(self) -> str:
        return random.choice(self.USER_AGENTS)

    def _check_file_size(self, file_path: Path, content_type: str) -> bool:
        if not file_path.exists():
            return False
        max_size = self.MAX_FILE_SIZES.get(content_type, 50 * 1024 * 1024)
        file_size = file_path.stat().st_size
        if file_size > max_size:
            logger.warning(f"File size {file_size} exceeds max {max_size}")
            file_path.unlink()
            return False
        return True

    # Путь к cookies файлам
    COOKIES_DIR = Path("/opt/uspsocdowloader")

    def _get_platform_opts(self, platform: str) -> dict:
        """Специальные опции для разных платформ"""
        opts = {
            "http_headers": {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        }

        if platform.lower() == "instagram":
            cookies_file = self.COOKIES_DIR / "instagram_cookies.txt"
            opts.update({
                "format": "best",
                "postprocessors": [],
                "extractor_args": {"instagram": {"skip": ["dash"]}},
                "sleep_interval": 2,
                "max_sleep_interval": 5,
            })
            if cookies_file.exists():
                opts["cookiefile"] = str(cookies_file)
                logger.info("Using Instagram cookies")
        elif platform.lower() == "tiktok":
            opts.update({
                "format": "best[ext=mp4]/best",
            })
        elif platform.lower() == "youtube":
            opts.update({
                "format": "best[height<=720][ext=mp4]/best[height<=720]/best",
            })

        return opts

    async def _download_with_retry(self, url: str, ydl_opts: dict, max_retries: int = 3) -> Optional[dict]:
        """Загрузка с повторными попытками"""
        import yt_dlp

        last_error = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = (attempt + 1) * 3 + random.uniform(1, 3)
                    logger.info(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s delay")
                    await asyncio.sleep(delay)
                    ydl_opts["http_headers"]["User-Agent"] = self._get_random_user_agent()

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    loop = asyncio.get_event_loop()
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                    return info

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed: {last_error[:100]}")

                if "429" in last_error or "Too Many" in last_error:
                    await asyncio.sleep(10 + random.uniform(1, 5))
                continue

        raise Exception(last_error or "Download failed after retries")

    def _find_recent_file(self, directory: Path, seconds: int = 120) -> Optional[str]:
        """Находит недавно созданный файл в директории"""
        try:
            for f in sorted(directory.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file() and f.stat().st_mtime > time.time() - seconds:
                    return str(f)
        except Exception as e:
            logger.error(f"Error finding recent file: {e}")
        return None

    def _find_recent_files(self, directory: Path, seconds: int = 120, count: int = 10) -> List[str]:
        """Находит несколько недавно созданных файлов в директории"""
        files = []
        try:
            for f in sorted(directory.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file() and f.stat().st_mtime > time.time() - seconds:
                    files.append(str(f))
                    if len(files) >= count:
                        break
        except Exception as e:
            logger.error(f"Error finding recent files: {e}")
        return files

    async def download_video(self, url: str, platform: str = "unknown") -> DownloadInfo:
        try:
            logger.info(f"Starting video download from {platform}: {url}")

            try:
                import yt_dlp
            except ImportError:
                return DownloadInfo(success=False, platform=platform,
                    error_message="yt-dlp не установлен")

            output_template = str(self.DOWNLOAD_DIRS["video"] / "%(title).50s_%(playlist_index|0)s.%(ext)s")

            ydl_opts = self.YDL_OPTS_VIDEO.copy()
            ydl_opts["outtmpl"] = output_template
            ydl_opts.update(self._get_platform_opts(platform))

            try:
                info = await self._download_with_retry(url, ydl_opts)
            except Exception as e:
                error_str = str(e)
                # Если нет видео - пробуем скачать как фото (Twitter/X часто содержит только картинки)
                if "No video" in error_str or "no video" in error_str.lower():
                    logger.info(f"No video found, trying to download as photo from {platform}")
                    return await self.download_twitter_photo(url, platform)
                raise

            if not info:
                return DownloadInfo(success=False, platform=platform,
                    error_message="Не удалось извлечь информацию о видео")

            # Проверяем, есть ли контент для скачивания (для VK wallposts без видео)
            entries = info.get("entries", [])
            if info.get("_type") == "playlist" and not entries:
                logger.warning(f"No downloadable content in {platform} post")
                if platform.lower() == "vk":
                    return DownloadInfo(success=False, platform=platform,
                        error_message="В этом посте нет видео. Фото из VK пока не поддерживаются.")
                return DownloadInfo(success=False, platform=platform,
                    error_message="В этом посте нет видео для скачивания")

            title = info.get("title", "Unknown")
            # Извлекаем описание поста (без ограничения - url_handler обрежет если нужно)
            description = info.get("description") or ""

            # Извлекаем метаданные
            author = info.get("channel") or info.get("uploader_id") or ""
            author_name = info.get("uploader") or ""
            likes = info.get("like_count")
            comments = info.get("comment_count")
            views = info.get("view_count")
            post_url = info.get("webpage_url") or url

            # Проверяем, является ли это плейлистом (Twitter с несколькими видео)
            n_entries = info.get("playlist_count") or len(entries) if entries else 1
            is_playlist = n_entries > 1
            
            if is_playlist:
                # Twitter с несколькими видео - обрабатываем как карусель
                logger.info(f"Detected playlist with {n_entries} entries from {platform}")
                downloaded_files = self._find_recent_files(self.DOWNLOAD_DIRS["video"], count=n_entries)
                
                if downloaded_files:
                    # Проверяем размер всех файлов
                    valid_files = []
                    total_size = 0
                    for fp in downloaded_files:
                        if os.path.exists(fp):
                            fsize = os.path.getsize(fp)
                            if fsize <= self.MAX_FILE_SIZES["video"]:
                                valid_files.append(fp)
                                total_size += fsize
                            else:
                                logger.warning(f"File too large, skipping: {fp} ({fsize} bytes)")
                    
                    if valid_files:
                        duration = info.get("duration")
                        logger.info(f"Multi-video downloaded: {title} ({len(valid_files)} files, {total_size} bytes)")
                        return DownloadInfo(
                            success=True, file_path=valid_files[0], file_paths=valid_files,
                            file_size=total_size, duration=duration, title=title, description=description,
                            author=author, author_name=author_name, likes=likes,
                            comments=comments, views=views, url=post_url, platform=platform,
                            is_carousel=True)
                    else:
                        return DownloadInfo(success=False, platform=platform,
                            error_message="Все видео слишком большие (максимум 100 MB каждое)")
                
                return DownloadInfo(success=False, platform=platform,
                    error_message="Файлы не найдены после загрузки")

            # Пробуем найти файл (одиночное видео)
            filename = self._find_recent_file(self.DOWNLOAD_DIRS["video"])

            if filename and os.path.exists(filename):
                if self._check_file_size(Path(filename), "video"):
                    file_size = os.path.getsize(filename)
                    duration = info.get("duration")
                    logger.info(f"Video downloaded: {title} ({file_size} bytes)")
                    return DownloadInfo(
                        success=True, file_path=filename, file_size=file_size,
                        duration=duration, title=title, description=description,
                        author=author, author_name=author_name, likes=likes,
                        comments=comments, views=views, url=post_url, platform=platform)
                else:
                    return DownloadInfo(success=False, platform=platform,
                        error_message="Видео слишком большое (максимум 100 MB)")

            return DownloadInfo(success=False, platform=platform,
                error_message="Файл не найден после загрузки")

        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            error_msg = str(e)[:150]
            if "429" in error_msg:
                error_msg = "Instagram временно заблокировал запросы. Попробуйте позже."
            return DownloadInfo(success=False, platform=platform, error_message=error_msg)

    async def download_audio(self, url: str, platform: str = "unknown") -> DownloadInfo:
        try:
            logger.info(f"Starting audio download from {platform}: {url}")
            import yt_dlp

            output_template = str(self.DOWNLOAD_DIRS["audio"] / "%(title).50s_%(playlist_index|0)s.%(ext)s")
            ydl_opts = self.YDL_OPTS_AUDIO.copy()
            ydl_opts["outtmpl"] = output_template
            ydl_opts.update(self._get_platform_opts(platform))

            info = await self._download_with_retry(url, ydl_opts)

            if info:
                title = info.get("title", "Unknown")
                filename = self._find_recent_file(self.DOWNLOAD_DIRS["audio"])

                if filename and os.path.exists(filename):
                    if self._check_file_size(Path(filename), "audio"):
                        file_size = os.path.getsize(filename)
                        return DownloadInfo(success=True, file_path=filename,
                            file_size=file_size, title=title, platform=platform)

            return DownloadInfo(success=False, platform=platform,
                error_message="Не удалось загрузить аудио")

        except Exception as e:
            return DownloadInfo(success=False, platform=platform,
                error_message=f"Ошибка: {str(e)[:100]}")

    async def download_twitter_photo(self, url: str, platform: str = "unknown") -> DownloadInfo:
        """Скачивает фото из Twitter/X твита используя gallery-dl"""
        try:
            logger.info(f"Starting Twitter photo download: {url}")
            import subprocess
            import aiohttp
            import json

            loop = asyncio.get_event_loop()

            # Используем gallery-dl -j для получения полных метаданных и URL
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["gallery-dl", "-j", url],
                    capture_output=True, text=True, timeout=30
                )
            )

            title = ""
            description = ""
            author = ""
            author_name = ""
            likes = None
            comments = None
            views = None
            post_url = url
            photo_urls = []

            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    for item in data:
                        if isinstance(item, list) and len(item) > 1:
                            # Элемент с URL изображения (тип 3)
                            if item[0] == 3 and isinstance(item[1], str):
                                if "pbs.twimg.com" in item[1]:
                                    photo_urls.append(item[1])
                                # Метаданные в item[2]
                                if len(item) > 2 and isinstance(item[2], dict):
                                    meta = item[2]
                                    if not description:
                                        description = meta.get("content", "")
                                    if not author:
                                        author = meta.get("user", {}).get("name", "")
                                    if not author_name:
                                        author_name = meta.get("user", {}).get("nick", "")
                                    if likes is None:
                                        likes = meta.get("favorite_count")
                                    if comments is None:
                                        comments = meta.get("reply_count")
                                    if views is None:
                                        views = meta.get("view_count")
                            # Элемент с метаданными (тип 2)
                            elif item[0] == 2 and isinstance(item[1], dict):
                                meta = item[1]
                                if not description:
                                    description = meta.get("content", "")
                                if not author:
                                    author = meta.get("user", {}).get("name", "")
                                if not author_name:
                                    author_name = meta.get("user", {}).get("nick", "")
                                if likes is None:
                                    likes = meta.get("favorite_count")
                                if comments is None:
                                    comments = meta.get("reply_count")
                                if views is None:
                                    views = meta.get("view_count")
                except json.JSONDecodeError:
                    logger.warning("Failed to parse gallery-dl JSON output")

            # Если JSON не сработал, пробуем обычный режим gallery-dl -g
            if not photo_urls:
                result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        ["gallery-dl", "-g", url],
                        capture_output=True, text=True, timeout=30
                    )
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        line = line.strip()
                        if line and "pbs.twimg.com" in line:
                            first_url = line.split("|")[0].strip()
                            if first_url and first_url not in photo_urls:
                                photo_urls.append(first_url)

            # Не ограничиваем описание здесь - url_handler сам решит, как отправить
            title = (description[:50] + "...") if description else "Twitter"

            if not photo_urls:
                return DownloadInfo(success=False, platform=platform,
                    error_message="Не найдены изображения в твите")

            logger.info(f"Found {len(photo_urls)} images in tweet")

            downloaded_files = []
            total_size = 0
            safe_title = "".join(c for c in str(title)[:40] if c.isalnum() or c in " -_").strip() or "twitter"

            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self._get_random_user_agent()}
                for i, photo_url in enumerate(photo_urls):
                    try:
                        async with session.get(photo_url, headers=headers) as resp:
                            if resp.status == 200:
                                content = await resp.read()
                                ext = "jpg"
                                if "format=png" in photo_url:
                                    ext = "png"
                                filename = str(self.DOWNLOAD_DIRS["photo"] / f"{safe_title}_{i}.{ext}")
                                with open(filename, "wb") as f:
                                    f.write(content)
                                downloaded_files.append(filename)
                                total_size += len(content)
                                logger.info(f"Twitter photo {i} downloaded: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to download photo {i}: {e}")

            if downloaded_files:
                if len(downloaded_files) == 1:
                    return DownloadInfo(
                        success=True, file_path=downloaded_files[0], file_size=total_size,
                        title=title, description=description, author=author,
                        author_name=author_name, likes=likes, comments=comments,
                        views=views, url=post_url, platform=platform)
                else:
                    # Несколько фото - как карусель
                    return DownloadInfo(
                        success=True, file_path=downloaded_files[0], file_paths=downloaded_files,
                        file_size=total_size, title=title, description=description,
                        author=author, author_name=author_name, likes=likes,
                        comments=comments, views=views, url=post_url,
                        platform=platform, is_carousel=True)

            return DownloadInfo(success=False, platform=platform,
                error_message="Не удалось скачать изображения")

        except Exception as e:
            logger.error(f"Error downloading Twitter photo: {str(e)}")
            return DownloadInfo(success=False, platform=platform,
                error_message=f"Ошибка: {str(e)[:100]}")

    async def download_photo(self, url: str, platform: str = "unknown") -> DownloadInfo:
        """Загружает фото - для Instagram скачивает через thumbnail"""
        try:
            logger.info(f"Starting photo download from {platform}: {url}")
            import yt_dlp
            import aiohttp

            # Получаем информацию о посте
            ydl_opts = self.YDL_OPTS_BASE.copy()
            ydl_opts.update(self._get_platform_opts(platform))
            ydl_opts["ignore_no_formats_error"] = True  # Игнорируем ошибку "no video"

            loop = asyncio.get_event_loop()

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))

            if not info:
                return DownloadInfo(success=False, platform=platform,
                    error_message="Не удалось получить информацию о фото")

            # Для постов с несколькими фото - берём первое
            entry = info
            if info.get("entries"):
                entry = info["entries"][0]

            title = entry.get("title", "Unknown")
            description = entry.get("description") or ""

            author = entry.get("channel") or entry.get("uploader_id") or ""
            likes = entry.get("like_count")
            comments = entry.get("comment_count")
            post_url = entry.get("webpage_url") or url

            # Получаем URL лучшего качества из thumbnails
            thumbnails = entry.get("thumbnails", [])
            if not thumbnails:
                return DownloadInfo(success=False, platform=platform,
                    error_message="Не найден URL фото")

            # Берём последний (обычно лучшее качество)
            photo_url = thumbnails[-1].get("url")
            if not photo_url:
                return DownloadInfo(success=False, platform=platform,
                    error_message="Не найден URL фото")

            # Скачиваем фото напрямую
            safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " -_").strip()
            filename = str(self.DOWNLOAD_DIRS["photo"] / f"{safe_title}.jpg")

            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self._get_random_user_agent()}
                async with session.get(photo_url, headers=headers) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(filename, "wb") as f:
                            f.write(content)
                        logger.info(f"Photo downloaded: {filename}")
                    else:
                        return DownloadInfo(success=False, platform=platform,
                            error_message=f"Ошибка загрузки фото: HTTP {resp.status}")

            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                return DownloadInfo(
                    success=True, file_path=filename, file_size=file_size,
                    title=title, description=description, author=author,
                    likes=likes, comments=comments, url=post_url, platform=platform)

            return DownloadInfo(success=False, platform=platform,
                error_message="Файл не сохранён")

        except Exception as e:
            logger.error(f"Error downloading photo: {str(e)}")
            return DownloadInfo(success=False, platform=platform,
                error_message=f"Ошибка: {str(e)[:100]}")

    async def download_instagram_gallery(self, url: str, platform: str = "instagram") -> DownloadInfo:
        """Скачивает Instagram пост (фото/карусель) через gallery-dl с cookies"""
        try:
            logger.info(f"Starting Instagram gallery download: {url}")
            import subprocess
            import aiohttp
            import json

            loop = asyncio.get_event_loop()
            cookies_file = self.COOKIES_DIR / "instagram_cookies.txt"

            if not cookies_file.exists():
                logger.warning("Instagram cookies not found, trying without auth")
                cookies_arg = []
            else:
                cookies_arg = ["--cookies", str(cookies_file)]

            # Используем gallery-dl -j для получения JSON с метаданными и URL
            cmd = ["gallery-dl", "-j"] + cookies_arg + [url]
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            )

            if result.returncode != 0 or not result.stdout.strip():
                logger.error(f"gallery-dl failed: {result.stderr}")
                return DownloadInfo(success=False, platform=platform,
                    error_message="Не удалось получить информацию о посте Instagram")

            # Парсим JSON
            description = ""
            author = ""
            author_name = ""
            likes = None
            comments = None
            post_url = url
            photo_urls = []

            try:
                data = json.loads(result.stdout)
                for item in data:
                    if isinstance(item, list) and len(item) > 1:
                        # Метаданные поста (тип 2)
                        if item[0] == 2 and isinstance(item[1], dict):
                            meta = item[1]
                            if not description:
                                description = meta.get("description", "")
                            if not author:
                                author = meta.get("username", "")
                            if not author_name:
                                author_name = meta.get("fullname", "")
                            if likes is None:
                                likes = meta.get("likes")
                            if comments is None:
                                comments = meta.get("comments")
                            if not post_url or post_url == url:
                                post_url = meta.get("post_url", url)

                        # URL изображения (тип 3)
                        elif item[0] == 3 and isinstance(item[1], str):
                            img_url = item[1]
                            # Только URL изображений из поста (cdninstagram.com, исключаем profile pic)
                            if "cdninstagram.com" in img_url and "/v/t51" in img_url:
                                photo_urls.append(img_url)
                            # Метаданные в item[2]
                            if len(item) > 2 and isinstance(item[2], dict):
                                meta = item[2]
                                if not description:
                                    description = meta.get("description", "")
                                if not author:
                                    author = meta.get("username", "")
                                if not author_name:
                                    author_name = meta.get("fullname", "")
                                if likes is None:
                                    likes = meta.get("likes")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse gallery-dl JSON: {e}")
                return DownloadInfo(success=False, platform=platform,
                    error_message="Ошибка парсинга данных Instagram")

            if not photo_urls:
                return DownloadInfo(success=False, platform=platform,
                    error_message="Не найдены изображения в посте")

            logger.info(f"Found {len(photo_urls)} images in Instagram post")

            # Скачиваем фото
            downloaded_files = []
            total_size = 0
            safe_title = "".join(c for c in str(author)[:30] if c.isalnum() or c in " -_").strip() or "instagram"

            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self._get_random_user_agent()}
                for i, photo_url in enumerate(photo_urls):
                    try:
                        async with session.get(photo_url, headers=headers) as resp:
                            if resp.status == 200:
                                content = await resp.read()
                                ext = "jpg"
                                filename = str(self.DOWNLOAD_DIRS["photo"] / f"{safe_title}_{i}.{ext}")
                                with open(filename, "wb") as f:
                                    f.write(content)
                                downloaded_files.append(filename)
                                total_size += len(content)
                                logger.info(f"Instagram photo {i} downloaded: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to download photo {i}: {e}")

            if downloaded_files:
                is_carousel = len(downloaded_files) > 1
                return DownloadInfo(
                    success=True,
                    file_path=downloaded_files[0],
                    file_paths=downloaded_files if is_carousel else None,
                    file_size=total_size,
                    description=description,
                    author=author,
                    author_name=author_name,
                    likes=likes,
                    comments=comments,
                    url=post_url,
                    platform=platform,
                    is_carousel=is_carousel
                )

            return DownloadInfo(success=False, platform=platform,
                error_message="Не удалось скачать изображения")

        except Exception as e:
            logger.error(f"Error downloading Instagram gallery: {str(e)}")
            return DownloadInfo(success=False, platform=platform,
                error_message=f"Ошибка: {str(e)[:100]}")

    async def download_carousel(self, url: str, platform: str = "unknown") -> DownloadInfo:
        """Скачивает карусель (пост с несколькими фото/видео)"""
        try:
            logger.info(f"Starting carousel download from {platform}: {url}")

            # Для Instagram используем gallery-dl (работает лучше с фото-каруселями)
            if platform.lower() == "instagram":
                return await self.download_instagram_gallery(url, platform)

            import yt_dlp
            import aiohttp

            ydl_opts = self.YDL_OPTS_BASE.copy()
            ydl_opts.update(self._get_platform_opts(platform))
            ydl_opts["ignore_no_formats_error"] = True

            loop = asyncio.get_event_loop()

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))

            if not info or not info.get("entries"):
                return DownloadInfo(success=False, platform=platform,
                    error_message="Не удалось получить информацию о карусели")

            entries = info.get("entries", [])
            logger.info(f"Carousel has {len(entries)} items")

            # Метаданные из первого элемента
            first = entries[0]
            description = first.get("description") or ""
            author = first.get("channel") or first.get("uploader_id") or ""
            likes = first.get("like_count")
            comments = first.get("comment_count")
            post_url = info.get("webpage_url") or url

            downloaded_files = []
            total_size = 0

            for i, entry in enumerate(entries):
                has_video = len(entry.get("formats", [])) > 0
                title = entry.get("title", f"media_{i}")
                safe_title = "".join(c for c in title[:40] if c.isalnum() or c in " -_").strip()

                if has_video:
                    # Скачиваем видео через yt-dlp
                    video_opts = self.YDL_OPTS_VIDEO.copy()
                    video_opts["outtmpl"] = str(self.DOWNLOAD_DIRS["video"] / f"{safe_title}_{i}.%(ext)s")
                    video_opts.update(self._get_platform_opts(platform))

                    entry_url = entry.get("webpage_url") or entry.get("url")
                    if entry_url:
                        with yt_dlp.YoutubeDL(video_opts) as ydl:
                            await loop.run_in_executor(None, lambda u=entry_url: ydl.download([u]))

                        video_file = self._find_recent_file(self.DOWNLOAD_DIRS["video"], seconds=60)
                        if video_file and os.path.exists(video_file):
                            downloaded_files.append(("video", video_file))
                            total_size += os.path.getsize(video_file)
                            logger.info(f"Carousel video {i} downloaded: {video_file}")
                else:
                    # Скачиваем фото через thumbnail
                    thumbnails = entry.get("thumbnails", [])
                    if thumbnails:
                        photo_url = thumbnails[-1].get("url")
                        if photo_url:
                            filename = str(self.DOWNLOAD_DIRS["photo"] / f"{safe_title}_{i}.jpg")
                            async with aiohttp.ClientSession() as session:
                                headers = {"User-Agent": self._get_random_user_agent()}
                                async with session.get(photo_url, headers=headers) as resp:
                                    if resp.status == 200:
                                        content = await resp.read()
                                        with open(filename, "wb") as f:
                                            f.write(content)
                                        downloaded_files.append(("photo", filename))
                                        total_size += os.path.getsize(filename)
                                        logger.info(f"Carousel photo {i} downloaded: {filename}")

            if downloaded_files:
                file_paths = [f[1] for f in downloaded_files]
                return DownloadInfo(
                    success=True,
                    file_path=file_paths[0],
                    file_paths=file_paths,
                    file_size=total_size,
                    description=description,
                    author=author,
                    likes=likes,
                    comments=comments,
                    url=post_url,
                    platform=platform,
                    is_carousel=True
                )

            return DownloadInfo(success=False, platform=platform,
                error_message="Не удалось скачать ни одного файла из карусели")

        except Exception as e:
            logger.error(f"Error downloading carousel: {str(e)}")
            return DownloadInfo(success=False, platform=platform,
                error_message=f"Ошибка: {str(e)[:100]}")

    async def download(self, url: str, content_type: str = "video", platform: str = "unknown") -> DownloadInfo:
        # Для Instagram постов проверяем - может быть карусель
        if platform.lower() == "instagram" and content_type in ["photo", "post", "carousel"]:
            return await self.download_carousel(url, platform)
        if content_type == "audio":
            return await self.download_audio(url, platform)
        elif content_type == "photo":
            return await self.download_photo(url, platform)
        else:
            return await self.download_video(url, platform)

    def cleanup_old_files(self, days: int = 1):
        import time
        try:
            current_time = time.time()
            threshold = current_time - (days * 24 * 60 * 60)
            for dir_path in self.DOWNLOAD_DIRS.values():
                if not dir_path.exists():
                    continue
                for file_path in dir_path.glob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime < threshold:
                        file_path.unlink()
        except Exception as e:
            logger.error(f"Error cleaning up: {str(e)}")
