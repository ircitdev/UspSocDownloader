# 📚 API Documentation - UspSocDownloader

> Техническая документация для разработчиков

---

## 🗄️ Database API

### DatabaseManager

Менеджер SQLite базы данных для хранения пользовательских данных.

#### Инициализация

```python
from src.database.db_manager import init_database, get_db_manager

# Инициализация
db = init_database(db_path)

# Получение экземпляра
db = get_db_manager()
```

#### User Settings

**get_user_settings(user_id: int) -> Dict[str, Any]**
```python
settings = await db.get_user_settings(123456789)
# Returns: {
#     'user_id': 123456789,
#     'default_quality': '720p',
#     'default_format': 'mp4',
#     'language': 'ru',
#     'auto_delete_after_days': 7,
#     'notifications_enabled': True
# }
```

**update_user_settings(user_id: int, **kwargs) -> bool**
```python
success = await db.update_user_settings(
    user_id=123456789,
    default_quality='1080p',
    default_format='webm'
)
```

#### Download History

**add_download_history(...) -> Optional[int]**
```python
download_id = await db.add_download_history(
    user_id=123456789,
    url="https://youtube.com/watch?v=ABC",
    platform="YouTube",
    content_type="video",
    file_path="/path/to/file.mp4",
    file_size=5242880,  # bytes
    title="Video Title",
    author="Channel Name",
    thumbnail_url="https://..."
)
```

**get_download_history(...) -> List[Dict[str, Any]]**
```python
history = await db.get_download_history(
    user_id=123456789,
    limit=50,
    offset=0,
    platform="YouTube",  # optional
    favorites_only=False  # optional
)
```

**get_download_by_id(download_id: int) -> Optional[Dict[str, Any]]**
```python
download = await db.get_download_by_id(42)
```

#### Favorites

**add_to_favorites(download_id: int) -> bool**
```python
success = await db.add_to_favorites(42)
```

**remove_from_favorites(download_id: int) -> bool**
```python
success = await db.remove_from_favorites(42)
```

#### Collections

**create_collection(...) -> Optional[int]**
```python
collection_id = await db.create_collection(
    user_id=123456789,
    name="My Collection",
    description="Optional description",
    icon="📁"
)
```

**get_collections(user_id: int) -> List[Dict[str, Any]]**
```python
collections = await db.get_collections(123456789)
```

**get_collection_by_id(collection_id: int) -> Optional[Dict[str, Any]]**
```python
collection = await db.get_collection_by_id(1)
```

**update_collection(...) -> bool**
```python
success = await db.update_collection(
    collection_id=1,
    name="Updated Name",  # optional
    icon="📸"  # optional
)
```

**delete_collection(collection_id: int) -> bool**
```python
success = await db.delete_collection(1)
# Unlinks all items from collection before deletion
```

**add_to_collection(download_id: int, collection_id: int) -> bool**
```python
success = await db.add_to_collection(42, 1)
```

**get_collection_items(collection_id: int) -> List[Dict[str, Any]]**
```python
items = await db.get_collection_items(1)
```

---

## 📤 Export API

### HistoryExporter

Экспорт истории загрузок в различные форматы.

#### Методы класса

**to_csv(history: List[Dict], include_metadata: bool = True) -> str**
```python
from src.utils.history_exporter import HistoryExporter

exporter = HistoryExporter()
csv_content = exporter.to_csv(history, include_metadata=True)
```

**to_json(history: List[Dict], pretty: bool = True, include_file_paths: bool = False) -> str**
```python
json_content = exporter.to_json(
    history,
    pretty=True,
    include_file_paths=False
)
```

**generate_filename(user_id: int, format_type: str) -> str**
```python
filename = exporter.generate_filename(123456789, 'csv')
# Returns: "download_history_123456789_20260302_153045.csv"
```

**save_to_file(content: str, file_path: Path, encoding: str = 'utf-8') -> bool**
```python
from pathlib import Path

success = exporter.save_to_file(
    content,
    Path("exports/history.csv")
)
```

**get_export_stats(history: List[Dict]) -> Dict[str, Any]**
```python
stats = exporter.get_export_stats(history)
# Returns: {
#     'total_downloads': 42,
#     'total_size_mb': 523.5,
#     'platforms': {'Instagram': 20, 'YouTube': 22},
#     'favorites': 5,
#     'date_range': {'first': '2026-01-01', 'last': '2026-03-02'}
# }
```

#### Helper Function

**export_user_history(...) -> tuple[str, Dict]**
```python
from src.utils.history_exporter import export_user_history

content, stats = await export_user_history(
    db=db,
    user_id=123456789,
    format_type='csv',  # or 'json'
    limit=None,  # optional
    platform='Instagram',  # optional
    favorites_only=False  # optional
)
```

---

## 🔍 Search API

### HistorySearcher

Поиск по истории загрузок с множественными фильтрами.

#### Методы класса

**search(...) -> List[Dict[str, Any]]**
```python
from src.utils.history_search import HistorySearcher
from datetime import datetime, timedelta

results = await HistorySearcher.search(
    user_id=123456789,
    query="sunset",  # optional, searches in title, author, url
    platform="Instagram",  # optional
    content_type="video",  # optional
    date_from=datetime.now() - timedelta(days=7),  # optional
    date_to=datetime.now(),  # optional
    favorites_only=False,  # optional
    limit=50
)
```

**search_by_date_range(user_id: int, days: int = 7, limit: int = 50) -> List[Dict]**
```python
results = await HistorySearcher.search_by_date_range(
    user_id=123456789,
    days=7
)
```

**search_by_author(user_id: int, author: str, limit: int = 50) -> List[Dict]**
```python
results = await HistorySearcher.search_by_author(
    user_id=123456789,
    author="john_photo"
)
```

**get_search_suggestions(user_id: int) -> Dict[str, Any]**
```python
suggestions = await HistorySearcher.get_search_suggestions(123456789)
# Returns: {
#     'platforms': ['Instagram', 'YouTube'],
#     'authors': ['john_photo', 'tech_guru'],
#     'content_types': ['video', 'photo'],
#     'total_downloads': 42
# }
```

**format_search_results(results: List[Dict], query: Optional[str] = None) -> str**
```python
formatted_text = HistorySearcher.format_search_results(
    results,
    query="sunset"
)
# Returns formatted Telegram message text with HTML
```

---

## 🗑️ File Cleanup API

### FileCleanupService

Автоматическая очистка старых файлов на основе настроек пользователя.

#### Инициализация

```python
from src.utils.file_cleaner import init_cleanup_service, get_cleanup_service

# Инициализация
cleanup_service = init_cleanup_service(cleanup_interval_hours=6)

# Запуск
await cleanup_service.start()

# Остановка
await cleanup_service.stop()

# Получение экземпляра
cleanup_service = get_cleanup_service()
```

#### Методы

**start() -> None**
```python
await cleanup_service.start()
# Starts background cleanup loop
```

**stop() -> None**
```python
await cleanup_service.stop()
# Stops background cleanup loop
```

**manual_cleanup(user_id: Optional[int] = None) -> Dict[str, Any]**
```python
# Cleanup for specific user
result = await cleanup_service.manual_cleanup(user_id=123456789)
# Returns: {
#     'user_id': 123456789,
#     'files_deleted': 5,
#     'space_freed_mb': 42.5
# }

# Cleanup for all users
result = await cleanup_service.manual_cleanup()
# Returns: {
#     'users_cleaned': 10,
#     'files_deleted': 50,
#     'space_freed_mb': 425.3
# }
```

**get_stats() -> Dict[str, Any]**
```python
stats = cleanup_service.get_stats()
# Returns: {
#     'is_running': True,
#     'cleanup_interval_hours': 6,
#     'total_cleanup_runs': 42,
#     'total_files_deleted': 150,
#     'total_space_freed_mb': 1024.5,
#     'last_cleanup_time': '2026-03-02T15:30:00'
# }
```

---

## ⏱️ Rate Limiter API

### RateLimiter

Глобальный rate limiter для предотвращения блокировок платформ.

#### Использование

```python
from src.utils.rate_limiter import rate_limiter

# Wait before making request
await rate_limiter.wait_if_needed("instagram")
# Downloads can proceed safely

# Alternative: acquire method
await rate_limiter.acquire("youtube")
```

#### Методы

**wait_if_needed(platform: str) -> float**
```python
wait_time = await rate_limiter.wait_if_needed("instagram")
# Returns: time waited in seconds (0 if no wait needed)
```

**get_stats(platform: Optional[str] = None) -> Dict[str, any]**
```python
# Stats for specific platform
stats = rate_limiter.get_stats("instagram")
# Returns: {
#     'platform': 'instagram',
#     'request_count': 42,
#     'total_wait_time': 150.5,
#     'min_interval': 5.0,
#     'last_request': 1709398765.123
# }

# Stats for all platforms
all_stats = rate_limiter.get_stats()
# Returns dict with stats for each platform
```

**set_interval(platform: str, interval: float) -> None**
```python
rate_limiter.set_interval("instagram", 10.0)
# Changes minimum interval to 10 seconds
```

**reset_stats() -> None**
```python
rate_limiter.reset_stats()
# Resets counters (does not reset last request times)
```

---

## 💬 Error Messages API

### User-friendly error handling

```python
from src.utils.error_messages import (
    get_error_type_from_exception,
    get_user_friendly_error,
    format_error_with_retry
)

# Detect error type from exception
try:
    # some code
except Exception as e:
    error_type = get_error_type_from_exception(e)
    # Returns: "instagram_rate_limit", "timeout", etc.

# Get formatted error message
message = get_user_friendly_error(
    error_type="instagram_rate_limit",
    include_emoji=True,
    include_suggestion=True
)

# Format with retry button
message, keyboard_data = format_error_with_retry(
    error_type="timeout",
    original_url="https://..."
)
# Returns: (message_text, keyboard_data or None)
```

#### Available Error Types

```python
ERROR_MESSAGES = {
    # Instagram
    "instagram_rate_limit",
    "instagram_private",
    "instagram_login_required",

    # YouTube
    "youtube_age_restricted",
    "youtube_premium_only",

    # General
    "file_too_large",
    "timeout",
    "network_error",
    "invalid_url",
    "platform_not_supported",
    "download_failed",
    "geo_restricted",
    "copyright",
    "server_error",
    "daily_limit_exceeded"
}
```

---

## 🧪 Testing API

### Running Tests

```python
# Run all tests
python tests/test_all.py

# Run specific test module
python test_cleanup.py
python test_export.py
python test_search.py
python test_collection_edit.py
```

### Test Suite Structure

```python
from tests.test_all import TestRunner

runner = TestRunner()

# Assertions
runner.assert_true(condition, "Test name")
runner.assert_equal(actual, expected, "Test name")
runner.assert_not_none(value, "Test name")

# Summary
runner.print_summary()
# Prints: passed, failed, success rate
```

---

## 🔧 Configuration

### Config Variables

```python
from src.config import config

# Paths
config.BASE_DIR          # Project root
config.DATA_DIR          # Data directory
config.DATABASE_PATH     # SQLite database path
config.TEMP_DIR          # Temporary files

# Bot Settings
config.BOT_TOKEN         # Telegram bot token
config.ADMIN_ID          # Admin user ID
config.DEBUG             # Debug mode
config.LOG_LEVEL         # Logging level

# Features
config.MAX_FILE_SIZE     # Max download size
```

---

## 📊 Database Schema

### Tables

#### user_settings
```sql
CREATE TABLE user_settings (
    user_id INTEGER PRIMARY KEY,
    default_quality TEXT DEFAULT '720p',
    default_format TEXT DEFAULT 'mp4',
    language TEXT DEFAULT 'ru',
    auto_delete_after_days INTEGER DEFAULT 7,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### download_history
```sql
CREATE TABLE download_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    platform TEXT NOT NULL,
    content_type TEXT,
    file_path TEXT,
    file_size INTEGER,
    title TEXT,
    author TEXT,
    thumbnail_url TEXT,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_favorite BOOLEAN DEFAULT FALSE,
    collection_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES user_settings(user_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);
```

#### collections
```sql
CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT '📁',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_settings(user_id)
);
```

---

## 🚀 Performance Tips

### Database

1. **Use indices** for frequently queried columns
2. **Batch operations** when possible
3. **Connection pooling** via `@async_db_operation` decorator

### Rate Limiting

1. **Always use rate limiter** before platform requests
2. **Adjust intervals** based on platform response
3. **Monitor statistics** to optimize

### File Management

1. **Enable auto-cleanup** to save disk space
2. **Use favorites** for permanent storage
3. **Export regularly** for backups

---

## 🔌 Integration Examples

### Custom Bot Command

```python
from aiogram import Router
from aiogram.filters import Command
from src.database.db_manager import get_db_manager

router = Router()

@router.message(Command("custom"))
async def custom_command(message: types.Message):
    db = get_db_manager()
    user_id = message.from_user.id

    # Get user data
    settings = await db.get_user_settings(user_id)
    history = await db.get_download_history(user_id, limit=10)

    # Process and respond
    await message.answer(f"You have {len(history)} downloads")
```

### Export Integration

```python
from src.utils.history_exporter import export_user_history
import pandas as pd

# Export to CSV and analyze
content, stats = await export_user_history(
    db=db,
    user_id=user_id,
    format_type='csv'
)

# Load into pandas
df = pd.read_csv(io.StringIO(content))
print(df.groupby('platform')['file_size_mb'].sum())
```

---

**API Version:** 1.0
**Last Updated:** 02.03.2026
**Maintainer:** [@smit_support](https://t.me/smit_support)
