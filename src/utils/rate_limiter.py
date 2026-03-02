"""Global rate limiter for all download platforms."""
import asyncio
import time
import logging
from collections import defaultdict
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Глобальный rate limiter для всех платформ."""

    def __init__(self):
        """Инициализация rate limiter."""
        # Время последнего запроса по платформе
        self.last_request: Dict[str, float] = defaultdict(float)

        # Минимальные интервалы между запросами (секунды)
        self.min_intervals: Dict[str, float] = {
            "instagram": 5.0,   # 5 секунд между запросами Instagram
            "youtube": 1.0,     # 1 секунда для YouTube
            "tiktok": 2.0,      # 2 секунды для TikTok
            "vk": 2.0,          # 2 секунды для VK
            "twitter": 2.0,     # 2 секунды для Twitter/X
            "facebook": 3.0,    # 3 секунды для Facebook
        }

        # Блокировки для каждой платформы
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Счетчики запросов для мониторинга
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.wait_times: Dict[str, float] = defaultdict(float)

    async def wait_if_needed(self, platform: str) -> float:
        """Ждет если нужно соблюсти rate limit.

        Args:
            platform: Название платформы (instagram, youtube, etc.)

        Returns:
            Время ожидания в секундах (0 если не ждали)
        """
        platform_lower = platform.lower()

        async with self.locks[platform_lower]:
            min_interval = self.min_intervals.get(platform_lower, 1.0)
            last = self.last_request[platform_lower]

            wait_time = 0.0

            if last > 0:
                elapsed = time.time() - last
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    logger.info(
                        f"Rate limiting {platform}: waiting {wait_time:.1f}s "
                        f"(min interval: {min_interval}s)"
                    )
                    await asyncio.sleep(wait_time)

                    # Обновляем статистику
                    self.wait_times[platform_lower] += wait_time

            # Обновляем время последнего запроса
            self.last_request[platform_lower] = time.time()

            # Увеличиваем счетчик
            self.request_counts[platform_lower] += 1

            return wait_time

    async def acquire(self, platform: str) -> None:
        """Получить доступ для запроса (alias для wait_if_needed).

        Args:
            platform: Название платформы
        """
        await self.wait_if_needed(platform)

    def get_stats(self, platform: Optional[str] = None) -> Dict[str, any]:
        """Получить статистику rate limiter.

        Args:
            platform: Платформа для статистики (None = все)

        Returns:
            Словарь со статистикой
        """
        if platform:
            platform_lower = platform.lower()
            return {
                "platform": platform,
                "request_count": self.request_counts[platform_lower],
                "total_wait_time": self.wait_times[platform_lower],
                "min_interval": self.min_intervals.get(platform_lower, 1.0),
                "last_request": self.last_request.get(platform_lower, 0)
            }

        # Статистика по всем платформам
        stats = {}
        for platform_key in self.min_intervals.keys():
            stats[platform_key] = {
                "request_count": self.request_counts[platform_key],
                "total_wait_time": self.wait_times[platform_key],
                "min_interval": self.min_intervals[platform_key],
                "avg_wait_per_request": (
                    self.wait_times[platform_key] / self.request_counts[platform_key]
                    if self.request_counts[platform_key] > 0 else 0
                )
            }

        return stats

    def reset_stats(self) -> None:
        """Сбросить статистику (не сбрасывает последние времена запросов)."""
        self.request_counts.clear()
        self.wait_times.clear()
        logger.info("Rate limiter stats reset")

    def set_interval(self, platform: str, interval: float) -> None:
        """Установить интервал для платформы.

        Args:
            platform: Название платформы
            interval: Минимальный интервал в секундах
        """
        platform_lower = platform.lower()
        old_interval = self.min_intervals.get(platform_lower, 1.0)
        self.min_intervals[platform_lower] = interval
        logger.info(
            f"Changed rate limit for {platform}: "
            f"{old_interval}s -> {interval}s"
        )

    async def wait_for_platform_available(
        self,
        platform: str,
        timeout: float = 60.0
    ) -> bool:
        """Ждать пока платформа не станет доступной.

        Args:
            platform: Название платформы
            timeout: Максимальное время ожидания

        Returns:
            True если дождались, False если таймаут
        """
        platform_lower = platform.lower()
        start_time = time.time()

        while True:
            # Проверяем доступность
            last = self.last_request[platform_lower]
            if last == 0:
                return True

            min_interval = self.min_intervals.get(platform_lower, 1.0)
            elapsed = time.time() - last

            if elapsed >= min_interval:
                return True

            # Проверяем таймаут
            if time.time() - start_time >= timeout:
                logger.warning(
                    f"Timeout waiting for {platform} to be available"
                )
                return False

            # Ждем немного и проверяем снова
            await asyncio.sleep(0.5)


# Глобальный экземпляр rate limiter
rate_limiter = RateLimiter()


async def with_rate_limit(platform: str, func, *args, **kwargs):
    """Декоратор-хелпер для выполнения функции с rate limit.

    Args:
        platform: Платформа
        func: Функция для выполнения
        *args, **kwargs: Аргументы функции

    Returns:
        Результат функции
    """
    await rate_limiter.wait_if_needed(platform)
    return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
