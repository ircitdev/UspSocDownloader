"""
Модуль интеграции с Google Sheets для статистики и трекинга
"""
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Google Sheets configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Spreadsheet ID from URL
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID", "1cQhOc-FyY5uF7cLC2nH0jht2pITrt0bc3swhvfhVUoI")

# Service account credentials path or JSON string
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "/opt/uspsocdowloader/credentials/google_service_account.json")
CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")


class GoogleSheetsManager:
    """Менеджер для работы с Google Sheets"""

    # Sheet names
    SHEET_USERS = "Users"
    SHEET_REQUESTS = "Requests"
    SHEET_STATS = "Stats"
    SHEET_ERRORS = "Errors"

    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def init(self) -> bool:
        """Инициализация подключения к Google Sheets"""
        if not GSPREAD_AVAILABLE:
            logger.warning("gspread not installed. Google Sheets integration disabled.")
            return False

        async with self._lock:
            if self._initialized:
                return True

            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._sync_init)
                self._initialized = True
                logger.info("Google Sheets connected successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Google Sheets: {e}")
                return False

    def _sync_init(self):
        """Синхронная инициализация (выполняется в executor)"""
        # Load credentials
        if CREDENTIALS_JSON:
            creds_dict = json.loads(CREDENTIALS_JSON)
            credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        elif Path(CREDENTIALS_PATH).exists():
            credentials = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        else:
            raise FileNotFoundError(f"Google credentials not found at {CREDENTIALS_PATH}")

        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)

        # Create sheets if not exist
        self._ensure_sheets_exist()

    def _ensure_sheets_exist(self):
        """Создает листы если они не существуют"""
        existing_sheets = [ws.title for ws in self.spreadsheet.worksheets()]

        # Users sheet
        if self.SHEET_USERS not in existing_sheets:
            ws = self.spreadsheet.add_worksheet(title=self.SHEET_USERS, rows=1000, cols=15)
            ws.append_row([
                "user_id", "username", "first_name", "last_name", "language",
                "first_seen", "last_seen", "total_requests", "status", "referrer_id",
                "is_premium", "is_bot", "notes"
            ])
            logger.info(f"Created sheet: {self.SHEET_USERS}")

        # Requests sheet
        if self.SHEET_REQUESTS not in existing_sheets:
            ws = self.spreadsheet.add_worksheet(title=self.SHEET_REQUESTS, rows=10000, cols=20)
            ws.append_row([
                "timestamp", "user_id", "username", "platform", "content_type",
                "url", "success", "file_size_mb", "duration_sec", "error_message",
                "processing_time_sec", "ai_used", "ai_type"
            ])
            logger.info(f"Created sheet: {self.SHEET_REQUESTS}")

        # Stats sheet (daily aggregates)
        if self.SHEET_STATS not in existing_sheets:
            ws = self.spreadsheet.add_worksheet(title=self.SHEET_STATS, rows=1000, cols=15)
            ws.append_row([
                "date", "total_users", "new_users", "active_users", "total_requests",
                "successful_requests", "failed_requests", "instagram_requests",
                "youtube_requests", "tiktok_requests", "twitter_requests", "vk_requests",
                "total_mb_downloaded", "ai_translations", "ai_rewrites", "ai_ocr"
            ])
            logger.info(f"Created sheet: {self.SHEET_STATS}")

        # Errors sheet
        if self.SHEET_ERRORS not in existing_sheets:
            ws = self.spreadsheet.add_worksheet(title=self.SHEET_ERRORS, rows=5000, cols=10)
            ws.append_row([
                "timestamp", "user_id", "error_type", "error_message", "url",
                "platform", "traceback"
            ])
            logger.info(f"Created sheet: {self.SHEET_ERRORS}")

    async def register_user(self, user_id: int, username: str = None,
                           first_name: str = None, last_name: str = None,
                           language: str = None, is_premium: bool = False,
                           is_bot: bool = False, referrer_id: int = None) -> bool:
        """Регистрирует нового пользователя или обновляет существующего"""
        if not await self.init():
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._sync_register_user,
                user_id, username, first_name, last_name, language,
                is_premium, is_bot, referrer_id
            )
            return True
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            return False

    def _sync_register_user(self, user_id: int, username: str, first_name: str,
                           last_name: str, language: str, is_premium: bool,
                           is_bot: bool, referrer_id: int):
        """Синхронная регистрация пользователя"""
        ws = self.spreadsheet.worksheet(self.SHEET_USERS)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check if user exists
        try:
            cell = ws.find(str(user_id), in_column=1)
            if cell:
                # Update last_seen and increment requests
                row = cell.row
                ws.update_cell(row, 7, now)  # last_seen
                current_requests = ws.cell(row, 8).value or "0"
                ws.update_cell(row, 8, int(current_requests) + 1)
                return
        except Exception as e:  # Cell not found or other error
            pass

        # New user
        ws.append_row([
            str(user_id),
            username or "",
            first_name or "",
            last_name or "",
            language or "ru",
            now,  # first_seen
            now,  # last_seen
            1,    # total_requests
            "active",
            str(referrer_id) if referrer_id else "",
            "yes" if is_premium else "no",
            "yes" if is_bot else "no",
            ""
        ])

    _request_counter = 0  # Counter for auto-updating stats
    
    async def log_request(self, user_id: int, username: str, platform: str,
                         content_type: str, url: str, success: bool,
                         file_size_mb: float = 0, duration_sec: float = 0,
                         error_message: str = None, processing_time: float = 0,
                         ai_used: bool = False, ai_type: str = None) -> bool:
        """Логирует запрос пользователя"""
        if not await self.init():
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._sync_log_request,
                user_id, username, platform, content_type, url, success,
                file_size_mb, duration_sec, error_message, processing_time,
                ai_used, ai_type
            )
            
            # Auto-update daily stats every 10 requests
            GoogleSheetsManager._request_counter += 1
            if GoogleSheetsManager._request_counter >= 10:
                GoogleSheetsManager._request_counter = 0
                await self.update_daily_stats()
            
            return True
        except Exception as e:
            logger.error(f"Error logging request: {e}")
            return False

    def _sync_log_request(self, user_id: int, username: str, platform: str,
                         content_type: str, url: str, success: bool,
                         file_size_mb: float, duration_sec: float,
                         error_message: str, processing_time: float,
                         ai_used: bool, ai_type: str):
        """Синхронное логирование запроса"""
        ws = self.spreadsheet.worksheet(self.SHEET_REQUESTS)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ws.append_row([
            now,
            str(user_id),
            username or "",
            platform or "",
            content_type or "",
            url[:500] if url else "",  # Limit URL length
            "yes" if success else "no",
            round(file_size_mb, 2) if file_size_mb else 0,
            round(duration_sec, 1) if duration_sec else 0,
            (error_message or "")[:200],  # Limit error message
            round(processing_time, 2) if processing_time else 0,
            "yes" if ai_used else "no",
            ai_type or ""
        ])

    async def log_error(self, user_id: int, error_type: str, error_message: str,
                       url: str = None, platform: str = None,
                       traceback: str = None) -> bool:
        """Логирует ошибку"""
        if not await self.init():
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._sync_log_error,
                user_id, error_type, error_message, url, platform, traceback
            )
            return True
        except Exception as e:
            logger.error(f"Error logging error: {e}")
            return False

    def _sync_log_error(self, user_id: int, error_type: str, error_message: str,
                       url: str, platform: str, traceback: str):
        """Синхронное логирование ошибки"""
        ws = self.spreadsheet.worksheet(self.SHEET_ERRORS)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ws.append_row([
            now,
            str(user_id),
            error_type or "",
            (error_message or "")[:500],
            (url or "")[:500],
            platform or "",
            (traceback or "")[:1000]
        ])

    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает статистику пользователя"""
        if not await self.init():
            return None

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_get_user_stats, user_id)
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None

    def _sync_get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Синхронное получение статистики пользователя"""
        ws = self.spreadsheet.worksheet(self.SHEET_USERS)
        try:
            cell = ws.find(str(user_id), in_column=1)
            if cell:
                row = ws.row_values(cell.row)
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "first_seen": row[5],
                    "last_seen": row[6],
                    "total_requests": int(row[7]) if row[7] else 0,
                    "status": row[8]
                }
        except Exception as e:  # Cell not found or other error
            pass
        return None


    async def update_daily_stats(self) -> bool:
        """Обновляет ежедневную статистику на основе данных из Requests"""
        if not await self.init():
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_update_daily_stats)
            return True
        except Exception as e:
            logger.error(f"Error updating daily stats: {e}")
            return False

    def _sync_update_daily_stats(self):
        """Синхронное обновление ежедневной статистики"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get all requests
        requests_ws = self.spreadsheet.worksheet(self.SHEET_REQUESTS)
        requests_data = requests_ws.get_all_records()
        
        # Get users count
        users_ws = self.spreadsheet.worksheet(self.SHEET_USERS)
        users_data = users_ws.get_all_records()
        total_users = len(users_data)
        
        # Filter today's requests
        today_requests = [r for r in requests_data if r.get('timestamp', '').startswith(today)]
        
        # Calculate stats
        total_requests = len(today_requests)
        successful = len([r for r in today_requests if r.get('success') == 'yes'])
        failed = len([r for r in today_requests if r.get('success') == 'no'])
        
        # Platform breakdown
        platforms = {'instagram': 0, 'youtube': 0, 'tiktok': 0, 'twitter': 0, 'vk': 0}
        total_mb = 0
        ai_translations = 0
        ai_rewrites = 0
        ai_ocr = 0
        active_users = set()
        
        for r in today_requests:
            platform = (r.get('platform') or '').lower()
            if platform in platforms:
                platforms[platform] += 1
            
            try:
                total_mb += float(r.get('file_size_mb') or 0)
            except:
                pass
            
            ai_type = r.get('ai_type', '').lower()
            if 'translat' in ai_type:
                ai_translations += 1
            elif 'rewrite' in ai_type:
                ai_rewrites += 1
            elif 'ocr' in ai_type:
                ai_ocr += 1
            
            active_users.add(r.get('user_id'))
        
        # Count new users today
        new_users = len([u for u in users_data if u.get('first_seen', '').startswith(today)])
        
        # Stats worksheet
        stats_ws = self.spreadsheet.worksheet(self.SHEET_STATS)
        
        # Check if today's row exists
        cell = stats_ws.find(today, in_column=1)
        row_data = [
            today, total_users, new_users, len(active_users), total_requests,
            successful, failed, platforms['instagram'], platforms['youtube'],
            platforms['tiktok'], platforms['twitter'], platforms['vk'],
            round(total_mb, 2), ai_translations, ai_rewrites, ai_ocr
        ]
        
        if cell:
            # Update existing row
            row = cell.row
            stats_ws.update(f'A{row}:P{row}', [row_data])
        else:
            # Add new row
            stats_ws.append_row(row_data)
        
        logger.info(f"Updated daily stats for {today}: {total_requests} requests, {successful} successful")



    async def get_user_daily_requests(self, user_id: int) -> int:
        """Возвращает количество успешных запросов пользователя за сегодня."""
        if not await self.init():
            return 0

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._sync_get_user_daily_requests,
                user_id
            )
        except Exception as e:
            logger.error(f"Error getting daily requests for {user_id}: {e}")
            return 0

    def _sync_get_user_daily_requests(self, user_id: int) -> int:
        """Синхронное получение количества запросов за сегодня."""
        today = datetime.now().strftime("%Y-%m-%d")
        ws = self.spreadsheet.worksheet(self.SHEET_REQUESTS)
        requests = ws.get_all_records()
        
        count = 0
        for r in requests:
            if (str(r.get('user_id')) == str(user_id) and 
                r.get('timestamp', '').startswith(today) and
                r.get('success') == 'yes'):
                count += 1
        
        return count

    async def is_user_premium(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь премиум."""
        if not await self.init():
            return False

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._sync_is_user_premium,
                user_id
            )
        except Exception as e:
            logger.error(f"Error checking premium for {user_id}: {e}")
            return False

    def _sync_is_user_premium(self, user_id: int) -> bool:
        """Синхронная проверка премиум статуса."""
        ws = self.spreadsheet.worksheet(self.SHEET_USERS)
        try:
            cell = ws.find(str(user_id), in_column=1)
            if cell:
                row = ws.row_values(cell.row)
                # Column 11 (index 10) is is_premium
                return len(row) > 10 and row[10].lower() == 'yes'
        except Exception:
            pass
        return False


# Singleton instance
sheets_manager = GoogleSheetsManager()
