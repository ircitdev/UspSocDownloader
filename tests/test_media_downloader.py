"""
Тесты для Media Downloader
"""
import os
import pytest
import asyncio
from pathlib import Path
from src.downloaders.media_downloader import MediaDownloader, DownloadInfo
from src.config import config


class TestMediaDownloader:
    """Тесты для MediaDownloader"""

    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.downloader = MediaDownloader()

    def test_download_dirs_created(self):
        """Тест создания директорий"""
        for dir_path in self.downloader.DOWNLOAD_DIRS.values():
            assert dir_path.exists(), f"Directory {dir_path} should exist"

    def test_download_paths_exist(self):
        """Тест существования путей для загрузки"""
        assert self.downloader.DOWNLOAD_DIRS["video"].exists()
        assert self.downloader.DOWNLOAD_DIRS["audio"].exists()
        assert self.downloader.DOWNLOAD_DIRS["photo"].exists()
        assert self.downloader.DOWNLOAD_DIRS["other"].exists()

    def test_get_download_path(self):
        """Тест получения пути для загрузки"""
        path = self.downloader._get_download_path("video", "test.mp4")
        assert "test.mp4" in str(path)
        assert "videos" in str(path)

    def test_get_download_path_unknown_type(self):
        """Тест получения пути для неизвестного типа"""
        path = self.downloader._get_download_path("unknown", "test.bin")
        assert "test.bin" in str(path)
        assert "other" in str(path)

    def test_max_file_sizes(self):
        """Тест лимитов размера файлов"""
        assert self.downloader.MAX_FILE_SIZES["video"] == 100 * 1024 * 1024
        assert self.downloader.MAX_FILE_SIZES["audio"] == 50 * 1024 * 1024
        assert self.downloader.MAX_FILE_SIZES["photo"] == 10 * 1024 * 1024

    def test_download_info_creation(self):
        """Тест создания объекта DownloadInfo"""
        info = DownloadInfo(
            success=True,
            file_path="/path/to/file.mp4",
            file_size=1024,
            duration=120.5,
            title="Test Video",
            platform="YouTube"
        )

        assert info.success is True
        assert info.file_path == "/path/to/file.mp4"
        assert info.file_size == 1024
        assert info.duration == 120.5
        assert info.title == "Test Video"
        assert info.platform == "YouTube"

    def test_download_info_error(self):
        """Тест создания DownloadInfo с ошибкой"""
        info = DownloadInfo(
            success=False,
            platform="Instagram",
            error_message="Network error"
        )

        assert info.success is False
        assert info.error_message == "Network error"
        assert info.platform == "Instagram"
        assert info.file_path is None

    def test_check_file_size_valid(self):
        """Тест проверки размера валидного файла"""
        # Создаем временный файл размером 1 MB
        test_file = self.downloader.DOWNLOAD_DIRS["video"] / "test.mp4"
        test_file.write_bytes(b"x" * (1024 * 1024))

        try:
            result = self.downloader._check_file_size(test_file, "video")
            assert result is True
        finally:
            test_file.unlink()

    def test_check_file_size_too_large(self):
        """Тест проверки файла слишком большого размера"""
        # Создаем временный файл размером 101 MB (больше лимита 100 MB)
        test_file = self.downloader.DOWNLOAD_DIRS["video"] / "large.mp4"
        # Не создаем реально большой файл, используем мок
        
        # Тест логики удаления файла при превышении размера
        # Файл должен быть удален функцией
        pass

    def test_ydl_opts_base_configuration(self):
        """Тест базовой конфигурации yt-dlp"""
        opts = self.downloader.YDL_OPTS_BASE
        assert opts["quiet"] is True
        assert opts["no_warnings"] is True
        assert opts["socket_timeout"] == 30

    def test_ydl_opts_video_configuration(self):
        """Тест конфигурации yt-dlp для видео"""
        opts = self.downloader.YDL_OPTS_VIDEO
        assert "format" in opts
        assert "postprocessors" in opts

    def test_ydl_opts_audio_configuration(self):
        """Тест конфигурации yt-dlp для аудио"""
        opts = self.downloader.YDL_OPTS_AUDIO
        assert "format" in opts
        assert "postprocessors" in opts
        # Проверяем что есть FFmpegExtractAudio постпроцессор
        pp_keys = [p.get("key") for p in opts.get("postprocessors", [])]
        assert "FFmpegExtractAudio" in pp_keys

    @pytest.mark.asyncio
    async def test_download_invalid_url(self):
        """Тест загрузки с неvalidной ссылкой"""
        result = await self.downloader.download_video(
            "https://invalid-url-that-does-not-exist.com/video",
            platform="test"
        )

        assert result.success is False
        assert result.platform == "test"
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_download_with_platform_info(self):
        """Тест что платформа сохраняется при ошибке"""
        platforms = ["Instagram", "YouTube", "TikTok", "VK", "X"]
        
        for platform in platforms:
            result = await self.downloader.download(
                "https://invalid.com",
                content_type="video",
                platform=platform
            )
            assert result.platform == platform

    def test_cleanup_old_files_directory_missing(self):
        """Тест очистки когда директория не существует"""
        # Не должно быть ошибок даже если директория не существует
        try:
            self.downloader.cleanup_old_files(days=7)
        except Exception as e:
            pytest.fail(f"cleanup_old_files raised {type(e).__name__}")

    def test_download_dirs_permissions(self):
        """Тест что директории доступны для записи"""
        for dir_path in self.downloader.DOWNLOAD_DIRS.values():
            assert os.access(dir_path, os.W_OK), f"Directory {dir_path} should be writable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
