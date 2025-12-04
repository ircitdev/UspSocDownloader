"""
Скрипт для демонстрации работы URL processor
"""
from src.processors.url_processor import URLProcessor, Platform

def demo():
    """Демонстрация работы"""
    processor = URLProcessor()

    print("\n" + "=" * 70)
    print("🤖 UspSocDownloader - Demo URL Processor")
    print("=" * 70 + "\n")

    # Тестовые ссылки
    test_urls = [
        "https://www.instagram.com/p/ABC123/",
        "https://instagram.com/reel/XYZ789/",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/abc123",
        "https://www.tiktok.com/@username/video/1234567890",
        "https://vm.tiktok.com/ZMhxxx/",
        "https://vk.com/wall-123_456",
        "https://www.vk.com/video-789_101",
        "https://twitter.com/username/status/1234567890",
        "https://x.com/user/status/9876543210",
        "https://google.com",
        "www.instagram.com/p/ABC123/",
    ]

    for url in test_urls:
        print(f"📎 URL: {url}")
        result = processor.process(url)

        if result.is_valid:
            print(f"   ✅ Платформа: {result.platform.value.upper()}")
            print(f"   📺 Тип контента: {result.content_type}")
            print(f"   🔑 ID поста: {result.post_id}")
        else:
            print(f"   ❌ Ошибка: {result.error_message}")

        print()

    print("=" * 70)
    print("✅ Demo завершен!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    demo()
