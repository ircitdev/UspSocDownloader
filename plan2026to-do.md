# План улучшения UspSocDownloader - 2026 TODO

## ✅ Выполнено

### Phase 1: База данных (22.02.2026)
- ✅ Создана SQLite база данных (`src/database/db_manager.py`)
- ✅ Таблицы: `user_settings`, `download_history`, `collections`
- ✅ Async операции через thread pool executor
- ✅ Интеграция в `url_handler.py` - сохранение истории после загрузки
- ✅ Тест скрипт (`test_db.py`) - все тесты пройдены
- ✅ Деплой на production сервер

### Phase 2: Настройки пользователя (22.02.2026)
- ✅ Команда `/settings` с интерактивным UI
- ✅ Настройка качества по умолчанию (360p, 480p, 720p, 1080p)
- ✅ Выбор формата видео (MP4, WebM)
- ✅ Период авто-удаления (3, 7, 14, 30 дней, никогда)
- ✅ Вкл/выкл уведомлений
- ✅ Проверка Premium для 1080p
- ✅ Callback handlers для всех настроек
- ✅ Деплой на production сервер

### Phase 3: История загрузок (22.02.2026)
- ✅ Команда `/history` показывает последние 10 загрузок
- ✅ Иконки платформ и метаданные (дата, размер)
- ✅ Кнопки "Скачать снова" для каждого элемента
- ✅ Умное кэширование - отправка из файла если существует
- ✅ Добавление/удаление из избранного (⭐/💔)
- ✅ Пагинация "Показать больше" с offset
- ✅ Кнопки в главном меню (История, Настройки)
- ✅ Callback handlers для redownload, favorites, pagination
- ✅ Деплой на production сервер

---

## 📋 В работе (Следующие шаги)

### Phase 4: Избранное и коллекции (2-3 дня)

#### 3.1 Команда `/history`
**Файл:** `src/handlers/commands.py`

**Функционал:**
```python
@router.message(Command("history"))
async def history_command(message: types.Message):
    """
    - Показать последние 10 загрузок
    - Иконка платформы (📸 Instagram, 📺 YouTube, etc.)
    - Дата и время в формате "22.02 14:30"
    - Размер файла в MB
    - Название (обрезать до 30 символов)
    - Inline кнопки для каждого элемента:
      - "Скачать снова" (redownload)
      - "⭐" (добавить в избранное)
    - Пагинация "Показать больше"
    """
```

**Пример вывода:**
```
📂 История загрузок

1. 📸 Красивый закат на море
   22.02 14:30 • 5.2 MB
2. 📺 Как готовить пасту карбонара
   22.02 12:15 • 12.5 MB
3. 🎵 Танцы в TikTok
   21.02 20:45 • 3.8 MB

[1. Скачать снова] [⭐]
[2. Скачать снова] [⭐]
[3. Скачать снова] [⭐]

📊 Показать больше
```

#### 3.2 Callback для повторной загрузки
**Callback:** `history_redownload_{download_id}`

**Логика:**
1. Получить запись из БД по `download_id`
2. Проверить что `user_id` совпадает
3. Если файл существует на диске → отправить сразу (из кэша)
4. Если файла нет → скачать заново через `url_handler`
5. Обновить дату в истории

#### 3.3 Интеграция в главное меню
**Файл:** `src/handlers/start.py`

Добавить кнопку в стартовое меню:
```python
[InlineKeyboardButton(text="📂 История", callback_data="show_history")]
```

#### 3.4 Добавить `/history` в команды бота
**Файл:** `src/bot.py`

```python
BotCommand(command="history", description="📂 История загрузок"),
```

---

### Phase 4: Избранное и коллекции (2-3 дня)

#### 4.1 Команда `/favorites`
**Функционал:**
- Показать все избранные загрузки
- Группировка по платформам (опционально)
- Быстрая отправка файла
- Удаление из избранного

#### 4.2 Команда `/collections`
**Функционал:**
- Список всех коллекций пользователя
- Создать коллекцию (имя + иконка)
- Переименовать коллекцию
- Удалить коллекцию
- Просмотреть элементы коллекции

#### 4.3 Кнопки после загрузки
**Файл:** `src/handlers/url_handler.py` (после строки 973)

После успешной загрузки добавить кнопки:
```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="⭐ В избранное", callback_data=f"add_favorite_{download_id}"),
        InlineKeyboardButton(text="📁 В коллекцию", callback_data=f"add_to_collection_{download_id}")
    ]
])

await message.answer("✅ Файл скачан!", reply_markup=keyboard)
```

---

### Phase 5: Улучшенная обработка ошибок (1-2 дня)

#### 5.1 Создать словарь понятных ошибок
**Файл:** `src/utils/error_messages.py` (новый)

```python
ERROR_MESSAGES = {
    "instagram_rate_limit": {
        "message": "Instagram временно ограничил доступ (слишком много запросов)",
        "suggestion": "Попробуйте через 5-10 минут",
        "retry_after": 300  # секунд
    },
    "instagram_private": {
        "message": "Этот пост приватный или удален",
        "suggestion": "Проверьте, что ссылка правильная и профиль публичный"
    },
    "youtube_age_restricted": {
        "message": "Видео с возрастными ограничениями",
        "suggestion": "К сожалению, такие видео недоступны"
    },
    "file_too_large": {
        "message": "Файл слишком большой для Telegram",
        "suggestion": "Попробуйте скачать в более низком качестве"
    },
    "timeout": {
        "message": "Превышено время ожидания",
        "suggestion": "Попробуйте позже или выберите меньшее качество"
    }
}

def get_user_friendly_error(error_type: str) -> str:
    """Возвращает понятное сообщение об ошибке."""
    error = ERROR_MESSAGES.get(error_type)
    if not error:
        return f"Произошла ошибка: {error_type}"

    return f"❌ {error['message']}\n\n💡 {error['suggestion']}"
```

#### 5.2 Кнопка "Повторить" при ошибках
**Файл:** `src/handlers/url_handler.py`

При ошибке вместо просто текста:
```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔄 Повторить", callback_data=f"retry_{message.message_id}")],
    [InlineKeyboardButton(text="❓ Помощь", callback_data="error_help")]
])

error_msg = get_user_friendly_error(error_type)
await message.answer(error_msg, reply_markup=keyboard)

# Кэшировать URL для retry
retry_cache[message.message_id] = {
    "url": url,
    "user_id": user_id,
    "timestamp": time.time()
}
```

---

### Phase 6: Rate Limiter для Instagram (1 день)

#### 6.1 Глобальная очередь запросов
**Файл:** `src/utils/rate_limiter.py` (новый)

```python
import asyncio
from collections import defaultdict
import time

class RateLimiter:
    """Глобальный rate limiter для всех платформ."""

    def __init__(self):
        self.last_request = defaultdict(float)
        self.min_intervals = {
            "instagram": 5,   # 5 секунд
            "youtube": 1,
            "tiktok": 2,
            "vk": 2,
            "twitter": 2
        }
        self.locks = defaultdict(asyncio.Lock)

    async def wait_if_needed(self, platform: str):
        """Ждет если нужно соблюсти rate limit."""
        async with self.locks[platform]:
            min_interval = self.min_intervals.get(platform, 1)
            last = self.last_request[platform]

            if last > 0:
                elapsed = time.time() - last
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    logger.info(f"Rate limiting {platform}: waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)

            self.last_request[platform] = time.time()

rate_limiter = RateLimiter()
```

#### 6.2 Интеграция в media_downloader
**Файл:** `src/downloaders/media_downloader.py`

В начале каждого метода `download_*`:
```python
from src.utils.rate_limiter import rate_limiter

async def download_instagram_gallery(self, url: str):
    # Ждем если нужно
    await rate_limiter.wait_if_needed("instagram")

    # Остальной код...
```

---

### Phase 7: Улучшенная аналитика (1-2 дня)

#### 7.1 Расширить `/allstats` (админ)
**Файл:** `src/handlers/commands.py`

**Новые метрики:**
- Топ-5 платформ (Instagram 45%, YouTube 30%, TikTok 15%, etc.)
- Средний размер файла
- Топ-5 часов пика активности
- Процент успешных vs неудачных загрузок
- Самые популярные настройки качества
- Количество созданных коллекций
- Количество избранных элементов

#### 7.2 Пользовательская статистика `/mystats`
**Файл:** `src/handlers/commands.py`

**Показывать:**
```
📊 Моя статистика

🎬 Всего загрузок: 142
📸 Любимая платформа: Instagram (65%)
💾 Скачано данных: 1.8 GB
⭐ В избранном: 23
📁 Коллекций: 5

📈 Активность по дням:
▓▓▓▓▓▓░░░░ Пн
▓▓▓▓▓▓▓▓▓░ Вт
▓▓▓▓▓▓▓▓▓▓ Ср
▓▓▓▓░░░░░░ Чт
```

---

## 🔮 Будущие улучшения (Month 2-3)

### Дополнительные функции
- [ ] **Batch downloads** - скачивание нескольких URL за раз
- [ ] **Scheduled downloads** - отложенная загрузка
- [ ] **Поиск по истории** - фильтры по платформе, дате, автору
- [ ] **Export истории** - в CSV/JSON
- [ ] **Web dashboard** для администратора
- [ ] **Telegram Mini App** для более богатого UI
- [ ] **Прогресс-бары** для больших загрузок
- [ ] **Webhooks** для интеграций

### Оптимизация
- [ ] **CDN для медиа** - ускорение загрузки
- [ ] **Redis кэш** - для часто скачиваемых файлов
- [ ] **Миграция на PostgreSQL** - для production масштаба
- [ ] **Kubernetes deployment** - масштабирование
- [ ] **Мониторинг** - Prometheus + Grafana

---

## 📝 Технические детали

### Структура БД (SQLite)

```sql
-- Настройки пользователя
user_settings (
    user_id INTEGER PRIMARY KEY,
    default_quality TEXT DEFAULT '720p',
    default_format TEXT DEFAULT 'mp4',
    language TEXT DEFAULT 'ru',
    auto_delete_after_days INTEGER DEFAULT 7,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

-- История загрузок
download_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    url TEXT,
    platform TEXT,  -- instagram, youtube, tiktok, vk, twitter
    content_type TEXT,  -- video, photo, audio, carousel
    file_path TEXT,
    file_size INTEGER,
    title TEXT,
    author TEXT,
    thumbnail_url TEXT,
    download_date TIMESTAMP,
    is_favorite BOOLEAN DEFAULT FALSE,
    collection_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES user_settings(user_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id)
)

-- Коллекции
collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    description TEXT,
    icon TEXT DEFAULT '📁',
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_settings(user_id)
)
```

### Индексы для производительности
```sql
CREATE INDEX idx_history_user_id ON download_history(user_id);
CREATE INDEX idx_history_date ON download_history(download_date DESC);
CREATE INDEX idx_history_platform ON download_history(platform);
CREATE INDEX idx_collections_user_id ON collections(user_id);
```

---

## 🚀 Deployment

### Локальное тестирование
```bash
# Тест базы данных
python test_db.py

# Запуск бота
python run_bot.py
```

### Production деплой
```bash
# На сервере 31.44.7.144
cd /opt/uspsocdowloader
git pull
systemctl restart uspsocdowloader
systemctl status uspsocdowloader

# Проверка логов
journalctl -u uspsocdowloader -f
```

### Проверка БД на сервере
```bash
ssh root@31.44.7.144
sqlite3 /opt/uspsocdowloader/data/bot_data.db

# SQL команды
.tables
SELECT COUNT(*) FROM user_settings;
SELECT COUNT(*) FROM download_history;
SELECT * FROM download_history ORDER BY download_date DESC LIMIT 5;
```

---

## 📊 Прогресс

**Неделя 1 (22.02 - 28.02):**
- ✅ Phase 1: База данных (22.02)
- ✅ Phase 2: Настройки (22.02)
- ⏳ Phase 3: История (23-25.02)
- ⏳ Phase 4: Избранное (26-28.02)

**Неделя 2 (01.03 - 07.03):**
- ⏳ Phase 5: Улучшенные ошибки (01-02.03)
- ⏳ Phase 6: Rate Limiter (03.03)
- ⏳ Phase 7: Аналитика (04-06.03)
- ⏳ Тестирование и баг-фиксы (07.03)

---

**Последнее обновление:** 22.02.2026
**Статус:** Phase 2 завершена ✅
**Следующий шаг:** Реализация Phase 3 (История загрузок)
