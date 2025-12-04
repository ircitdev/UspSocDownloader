"""
Тесты для URL Processor
"""
import pytest
from src.processors.url_processor import URLProcessor, Platform, URLInfo
from src.utils.validators import URLValidator, MessageValidator


class TestURLProcessor:
    """Тесты для URLProcessor"""

    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.processor = URLProcessor()

    # ===== Тесты определения платформы =====

    def test_detect_instagram_platform(self):
        """Тест определения Instagram"""
        urls = [
            "https://www.instagram.com/p/ABC123/",
            "https://instagram.com/reel/XYZ789/",
            "https://www.instagram.com/stories/username/123456/",
        ]
        for url in urls:
            assert self.processor.detect_platform(url) == Platform.INSTAGRAM

    def test_detect_youtube_platform(self):
        """Тест определения YouTube"""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/abc123",
        ]
        for url in urls:
            assert self.processor.detect_platform(url) == Platform.YOUTUBE

    def test_detect_tiktok_platform(self):
        """Тест определения TikTok"""
        urls = [
            "https://www.tiktok.com/@username/video/1234567890",
            "https://vm.tiktok.com/ZMhxxx/",
            "https://vt.tiktok.com/abc123/",
        ]
        for url in urls:
            assert self.processor.detect_platform(url) == Platform.TIKTOK

    def test_detect_vk_platform(self):
        """Тест определения VK"""
        urls = [
            "https://vk.com/wall-123_456",
            "https://www.vk.com/video-123_456",
            "https://vk.com/audio123_456",
        ]
        for url in urls:
            assert self.processor.detect_platform(url) == Platform.VK

    def test_detect_x_platform(self):
        """Тест определения X/Twitter"""
        urls = [
            "https://twitter.com/username/status/1234567890",
            "https://x.com/username/status/1234567890",
            "https://www.x.com/user/status/9876543210",
        ]
        for url in urls:
            assert self.processor.detect_platform(url) == Platform.X

    def test_detect_unknown_platform(self):
        """Тест неизвестной платформы"""
        assert self.processor.detect_platform("https://google.com") == Platform.UNKNOWN
        assert self.processor.detect_platform("") == Platform.UNKNOWN
        assert self.processor.detect_platform(None) == Platform.UNKNOWN

    # ===== Тесты Instagram =====

    def test_instagram_post_extraction(self):
        """Тест извлечения Instagram поста"""
        url = "https://www.instagram.com/p/ABC123/"
        post_id, content_type = self.processor.extract_instagram_id(url)
        assert post_id == "ABC123"
        assert content_type == "photo"

    def test_instagram_reel_extraction(self):
        """Тест извлечения Instagram рилса"""
        url = "https://instagram.com/reel/XYZ789/"
        post_id, content_type = self.processor.extract_instagram_id(url)
        assert post_id == "XYZ789"
        assert content_type == "reel"

    def test_instagram_story_extraction(self):
        """Тест извлечения Instagram истории"""
        url = "https://www.instagram.com/stories/username/123456/"
        post_id, content_type = self.processor.extract_instagram_id(url)
        assert post_id == "username"
        assert content_type == "story"

    # ===== Тесты YouTube =====

    def test_youtube_long_url_extraction(self):
        """Тест извлечения YouTube видео (длинный URL)"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id, content_type = self.processor.extract_youtube_id(url)
        assert video_id == "dQw4w9WgXcQ"
        assert content_type == "video"

    def test_youtube_short_url_extraction(self):
        """Тест извлечения YouTube видео (короткий URL)"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id, content_type = self.processor.extract_youtube_id(url)
        assert video_id == "dQw4w9WgXcQ"
        assert content_type == "video"

    def test_youtube_shorts_extraction(self):
        """Тест извлечения YouTube shorts"""
        url = "https://www.youtube.com/shorts/abc123"
        video_id, content_type = self.processor.extract_youtube_id(url)
        assert video_id == "abc123"
        assert content_type == "shorts"

    # ===== Тесты TikTok =====

    def test_tiktok_full_url_extraction(self):
        """Тест извлечения TikTok видео (полный URL)"""
        url = "https://www.tiktok.com/@username/video/1234567890"
        video_id, content_type = self.processor.extract_tiktok_id(url)
        assert video_id == "1234567890"
        assert content_type == "video"

    def test_tiktok_short_url_vm_extraction(self):
        """Тест извлечения TikTok (короткий URL vm.tiktok)"""
        url = "https://vm.tiktok.com/ZMhxxx/"
        video_id, content_type = self.processor.extract_tiktok_id(url)
        assert video_id == "ZMhxxx"
        assert content_type == "video"

    def test_tiktok_short_url_vt_extraction(self):
        """Тест извлечения TikTok (короткий URL vt.tiktok)"""
        url = "https://vt.tiktok.com/abc123/"
        video_id, content_type = self.processor.extract_tiktok_id(url)
        assert video_id == "abc123"
        assert content_type == "video"

    # ===== Главные тесты обработки =====

    def test_process_valid_instagram_url(self):
        """Тест обработки валидной Instagram ссылки"""
        url = "https://www.instagram.com/p/ABC123/"
        result = self.processor.process(url)

        assert isinstance(result, URLInfo)
        assert result.platform == Platform.INSTAGRAM
        assert result.post_id == "ABC123"
        assert result.content_type == "photo"
        assert result.is_valid is True
        assert result.error_message is None

    def test_process_valid_youtube_url(self):
        """Тест обработки валидной YouTube ссылки"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = self.processor.process(url)

        assert result.platform == Platform.YOUTUBE
        assert result.post_id == "dQw4w9WgXcQ"
        assert result.content_type == "video"
        assert result.is_valid is True

    def test_process_valid_tiktok_url(self):
        """Тест обработки валидной TikTok ссылки"""
        url = "https://vm.tiktok.com/ZMhxxx/"
        result = self.processor.process(url)

        assert result.platform == Platform.TIKTOK
        assert result.post_id == "ZMhxxx"
        assert result.is_valid is True

    def test_process_valid_vk_url(self):
        """Тест обработки валидной VK ссылки"""
        url = "https://vk.com/wall-123_456"
        result = self.processor.process(url)

        assert result.platform == Platform.VK
        assert result.post_id == "-123_456"
        assert result.is_valid is True

    def test_process_valid_x_url(self):
        """Тест обработки валидной X/Twitter ссылки"""
        url = "https://twitter.com/username/status/1234567890"
        result = self.processor.process(url)

        assert result.platform == Platform.X
        assert result.post_id == "1234567890"
        assert result.content_type == "tweet"
        assert result.is_valid is True

    def test_process_invalid_url_no_protocol(self):
        """Тест обработки URL без протокола"""
        url = "www.instagram.com/p/ABC123/"
        result = self.processor.process(url)

        assert result.is_valid is False
        assert result.error_message == "Ссылка должна начинаться с http:// или https://"

    def test_process_invalid_url_unsupported_platform(self):
        """Тест обработки URL неподдерживаемой платформы"""
        url = "https://google.com"
        result = self.processor.process(url)

        assert result.is_valid is False
        assert "Неподдерживаемая платформа" in result.error_message

    def test_process_empty_url(self):
        """Тест обработки пустой ссылки"""
        result = self.processor.process("")

        assert result.is_valid is False
        assert result.error_message == "URL не может быть пустым"

    def test_process_none_url(self):
        """Тест обработки None"""
        result = self.processor.process(None)

        assert result.is_valid is False


class TestURLValidator:
    """Тесты для URLValidator"""

    def test_is_valid_url(self):
        """Тест валидности URL"""
        assert URLValidator.is_valid_url("https://example.com")
        assert URLValidator.is_valid_url("http://example.com")
        assert not URLValidator.is_valid_url("example.com")
        assert not URLValidator.is_valid_url("")
        assert not URLValidator.is_valid_url(None)

    def test_is_instagram_url(self):
        """Тест определения Instagram URL"""
        assert URLValidator.is_instagram_url("https://instagram.com/p/ABC123/")
        assert not URLValidator.is_instagram_url("https://youtube.com")

    def test_is_youtube_url(self):
        """Тест определения YouTube URL"""
        assert URLValidator.is_youtube_url("https://youtube.com/watch?v=abc")
        assert URLValidator.is_youtube_url("https://youtu.be/abc")
        assert not URLValidator.is_youtube_url("https://instagram.com")

    def test_is_tiktok_url(self):
        """Тест определения TikTok URL"""
        assert URLValidator.is_tiktok_url("https://tiktok.com/@user/video/123")
        assert URLValidator.is_tiktok_url("https://vm.tiktok.com/abc")
        assert not URLValidator.is_tiktok_url("https://youtube.com")

    def test_is_vk_url(self):
        """Тест определения VK URL"""
        assert URLValidator.is_vk_url("https://vk.com/wall-123_456")
        assert URLValidator.is_vk_url("https://www.vk.com/video-123_456")
        assert not URLValidator.is_vk_url("https://instagram.com")

    def test_is_x_url(self):
        """Тест определения X/Twitter URL"""
        assert URLValidator.is_x_url("https://twitter.com/user/status/123")
        assert URLValidator.is_x_url("https://x.com/user/status/123")
        assert not URLValidator.is_x_url("https://youtube.com")

    def test_is_supported_platform(self):
        """Тест определения поддерживаемой платформы"""
        assert URLValidator.is_supported_platform("https://instagram.com/p/ABC123/")
        assert URLValidator.is_supported_platform("https://youtube.com/watch?v=abc")
        assert URLValidator.is_supported_platform("https://tiktok.com/@user/video/123")
        assert URLValidator.is_supported_platform("https://vk.com/wall-123_456")
        assert URLValidator.is_supported_platform("https://twitter.com/user/status/123")
        assert not URLValidator.is_supported_platform("https://google.com")


class TestMessageValidator:
    """Тесты для MessageValidator"""

    def test_is_valid_message(self):
        """Тест валидности сообщения"""
        assert MessageValidator.is_valid_message("Hello world")
        assert not MessageValidator.is_valid_message("")
        assert not MessageValidator.is_valid_message(None)

    def test_contains_url(self):
        """Тест определения URL в сообщении"""
        assert MessageValidator.contains_url("Check this: https://example.com")
        assert not MessageValidator.contains_url("No URLs here")
        assert not MessageValidator.contains_url("")

    def test_extract_urls(self):
        """Тест извлечения URL"""
        text = "Check https://instagram.com and https://youtube.com"
        urls = MessageValidator.extract_urls(text)
        assert len(urls) == 2
        assert "https://instagram.com" in urls
        assert "https://youtube.com" in urls

    def test_validate_and_extract_urls(self):
        """Тест валидации и извлечения URL"""
        # Valid message with URL
        is_valid, urls, error = MessageValidator.validate_and_extract_urls(
            "Download from https://instagram.com/p/ABC123/"
        )
        assert is_valid is True
        assert len(urls) == 1
        assert error is None

        # Invalid message without URL
        is_valid, urls, error = MessageValidator.validate_and_extract_urls("No URL here")
        assert is_valid is False
        assert len(urls) == 0
        assert error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
