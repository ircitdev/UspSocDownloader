"""Instagram health check module."""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from src.utils.logger import get_logger
from src.config import config

logger = get_logger(__name__)

COOKIES_FILE = Path("/opt/uspsocdowloader/instagram_cookies.txt")
TEST_URL = "https://www.instagram.com/instagram/"  # Official Instagram account


async def check_instagram_connection() -> Tuple[bool, str]:
    """
    Check if Instagram cookies are valid.
    Returns: (is_working, message)
    """
    try:
        if not COOKIES_FILE.exists():
            return False, "Файл cookies не найден"
        
        loop = asyncio.get_event_loop()
        
        def run_check():
            result = subprocess.run(
                ["gallery-dl", "-g", "--cookies", str(COOKIES_FILE), TEST_URL],
                capture_output=True, text=True, timeout=30
            )
            return result
        
        result = await loop.run_in_executor(None, run_check)
        
        if result.returncode == 0 and result.stdout.strip():
            return True, "Instagram подключение работает"
        
        stderr = result.stderr.lower()
        if "login" in stderr or "redirect" in stderr:
            return False, "Cookies устарели - требуется авторизация"
        elif "429" in stderr or "too many" in stderr:
            return False, "429 Too Many Requests - превышен лимит запросов"
        else:
            return False, f"Ошибка: {result.stderr[:100]}"
            
    except subprocess.TimeoutExpired:
        return False, "Таймаут проверки (30 сек)"
    except Exception as e:
        return False, f"Ошибка проверки: {str(e)[:100]}"


async def update_cookies(cookies_content: str) -> Tuple[bool, str]:
    """
    Update Instagram cookies file.
    Returns: (success, message)
    """
    try:
        # Validate cookies format
        lines = cookies_content.strip().split("\n")
        valid_lines = []
        has_sessionid = False
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                valid_lines.append(line)
                continue
            
            parts = line.split("\t")
            if len(parts) >= 7 and "instagram.com" in parts[0]:
                valid_lines.append(line)
                if "sessionid" in line.lower():
                    has_sessionid = True
        
        if not has_sessionid:
            return False, "В cookies не найден sessionid - невалидный формат"
        
        # Write to file
        COOKIES_FILE.write_text("\n".join(valid_lines) + "\n")
        logger.info("Instagram cookies updated")
        
        # Test new cookies
        is_working, message = await check_instagram_connection()
        
        if is_working:
            return True, "Cookies обновлены и проверены - Instagram работает!"
        else:
            return False, f"Cookies сохранены, но проверка не прошла: {message}"
            
    except Exception as e:
        logger.error(f"Error updating cookies: {e}")
        return False, f"Ошибка сохранения: {str(e)[:100]}"


class InstagramHealthChecker:
    """Periodic Instagram health checker."""
    
    def __init__(self, bot=None, check_interval_hours: int = 12):
        self.bot = bot
        self.check_interval = check_interval_hours * 3600  # Convert to seconds
        self._task: Optional[asyncio.Task] = None
        self._last_status: Optional[bool] = None
    
    def set_bot(self, bot):
        """Set bot instance for notifications."""
        self.bot = bot
    
    async def notify_admin(self, message: str, is_error: bool = True):
        """Send notification to admin."""
        if not self.bot or not config.ADMIN_ID:
            logger.warning("Cannot notify admin - bot or admin_id not set")
            return
        
        try:
            emoji = "🔴" if is_error else "🟢"
            await self.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=f"{emoji} <b>Instagram Health Check</b>\n\n{message}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
    
    async def run_check(self, notify_on_success: bool = False) -> Tuple[bool, str]:
        """Run health check and notify admin if there's a problem."""
        is_working, message = await check_instagram_connection()
        
        # Notify only on status change or if requested
        if not is_working:
            if self._last_status != False:  # Status changed to error
                await self.notify_admin(
                    f"{message}\n\n"
                    f"Для обновления cookies используйте:\n"
                    f"<code>/setcookies</code> и отправьте файл cookies",
                    is_error=True
                )
            self._last_status = False
        else:
            if notify_on_success or self._last_status == False:  # Recovered or explicit request
                await self.notify_admin(message, is_error=False)
            self._last_status = True
        
        return is_working, message
    
    async def _periodic_check(self):
        """Background task for periodic checks."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                logger.info("Running periodic Instagram health check")
                await self.run_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic health check: {e}")
    
    def start(self):
        """Start periodic health checker."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._periodic_check())
            logger.info(f"Instagram health checker started (interval: {self.check_interval // 3600}h)")
    
    def stop(self):
        """Stop periodic health checker."""
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Instagram health checker stopped")


# Singleton instance
instagram_health = InstagramHealthChecker()
