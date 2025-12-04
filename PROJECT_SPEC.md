# UspSocDownloader - Техническое задание

## 📋 Общая информация

**Название:** UspSocDownloader (Universal Social Media Downloader Bot)
**Тип:** Telegram Bot
**Telegram:** @UspSocDownloader_bot
**API Token:** `8511650801:AAEGVXeNJeHHhl-ryB8qvQ0dTLTNse-IDK0`

---

## 🎯 Цель проекта

Создать Telegram бота, который позволяет пользователям скачивать медиа-контент (видео, фото, карусели) из популярных социальных сетей вместе с текстом поста.

---

## 📱 Функциональные требования

### 1. Основной функционал

#### 1.1. Прием ссылок
- Пользователь отправляет ссылку на пост из соцсети
- Бот автоматически определяет платформу
- Поддержка различных форматов ссылок (короткие, полные, мобильные)

#### 1.2. Скачивание контента
- **Видео:**
  - Максимальное качество (до 1080p)
  - Автоматический выбор формата (mp4)
  - Поддержка длинных видео (до 50MB для Telegram)

- **Фото:**
  - Оригинальное качество
  - Поддержка альбомов/карусели

- **Карусели:**
  - Скачивание всех элементов
  - Отправка как MediaGroup

#### 1.3. Текст поста
- Извлечение описания/caption
- Сохранение форматирования
- Обрезка если слишком длинный (>1024 символов)
- Добавление информации об авторе

#### 1.4. Метаданные
- Автор поста
- Дата публикации
- Количество лайков/просмотров (если доступно)
- Хэштеги

---

## 🌐 Поддерживаемые платформы

### Приоритет 1 (MVP):
1. **Instagram**
   - Посты (фото/видео)
   - Reels
   - Stories (по возможности)
   - IGTV

2. **YouTube**
   - Обычные видео
   - Shorts
   - Автоматическое извлечение субтитров (опционально)

3. **TikTok**
   - Видео без водяного знака
   - Описание и автор
   - Музыка (опционально)

### Приоритет 2 (после MVP):
4. **Twitter/X**
   - Видео
   - Фото
   - GIF

5. **VK**
   - Видео
   - Фото
   - Альбомы

6. **Facebook**
   - Публичные видео
   - Фото

---

## 🏗️ Архитектура

### Компоненты системы

```
┌─────────────────┐
│  Telegram Bot   │
│   (aiogram)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Dispatcher    │ ← Обработка команд и сообщений
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ URL Processor   │ ← Определение платформы
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│    Platform Handlers            │
│  ┌──────────┬──────────┬─────┐  │
│  │Instagram │ YouTube  │TikTok│  │
│  └──────────┴──────────┴─────┘  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────┐
│   Downloader    │ ← yt-dlp / gallery-dl
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Media Processor │ ← Конвертация, сжатие
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Telegram API   │ ← Отправка файлов
└─────────────────┘
```

### Модули

1. **bot.py** - Инициализация бота
2. **handlers/** - Обработчики команд и сообщений
3. **downloaders/** - Загрузчики для каждой платформы
4. **processors/** - Обработка медиа
5. **utils/** - Вспомогательные функции
6. **config.py** - Конфигурация
7. **database/** - Работа с БД (опционально)

---

## 🛠️ Технологический стек

### Backend
- **Python 3.11+**
- **aiogram 3.x** - Telegram Bot framework
- **yt-dlp** - Универсальный загрузчик
- **gallery-dl** - Для Instagram/Twitter
- **aiohttp** - Async HTTP клиент
- **aiofiles** - Async работа с файлами
- **Pillow** - Обработка изображений
- **ffmpeg** - Обработка видео

### Хранение (опционально)
- **Redis** - Кэш, очередь задач
- **SQLite** - Статистика использования

### Инфраструктура
- **Docker** - Контейнеризация
- **Docker Compose** - Оркестрация
- **systemd** - Автозапуск (для VPS)

---

## 📊 Структура проекта

```
UspSocDownloader/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── bot.py                  # Bot initialization
│   ├── config.py               # Configuration
│   │
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py            # /start command
│   │   ├── help.py             # /help command
│   │   ├── url_handler.py      # URL processing
│   │   └── error_handler.py    # Error handling
│   │
│   ├── downloaders/
│   │   ├── __init__.py
│   │   ├── base.py             # Base downloader
│   │   ├── instagram.py        # Instagram
│   │   ├── youtube.py          # YouTube
│   │   ├── tiktok.py           # TikTok
│   │   ├── twitter.py          # Twitter
│   │   └── vk.py               # VK
│   │
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── url_processor.py    # URL parsing
│   │   ├── media_processor.py  # Media conversion
│   │   └── text_processor.py   # Text extraction
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py           # Logging
│   │   ├── file_utils.py       # File operations
│   │   └── validators.py       # URL validation
│   │
│   └── database/
│       ├── __init__.py
│       ├── models.py           # Data models
│       └── repository.py       # DB operations
│
├── tests/
│   ├── test_downloaders.py
│   ├── test_processors.py
│   └── test_handlers.py
│
├── data/                       # Temporary files
├── logs/                       # Log files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── README.md
```

---

## 🔐 Безопасность

### 1. Токены и секреты
- Хранение в `.env` файле
- Не коммитить в Git
- Использование environment variables

### 2. Ограничения
- Rate limiting (max requests per user)
- Максимальный размер файла (50MB для Telegram)
- Timeout для долгих загрузок

### 3. Валидация
- Проверка URL перед скачиванием
- Проверка типа файла
- Сканирование на вирусы (опционально)

---

## 📈 Масштабируемость

### Текущая версия (MVP)
- Однопоточная обработка
- Локальное хранение файлов
- SQLite для статистики

### Будущие улучшения
- Очередь задач (Celery + Redis)
- Распределенное хранилище (S3)
- Горизонтальное масштабирование
- CDN для медиа

---

## 🚀 Этапы разработки

### Phase 1: MVP (1-2 недели)
- ✅ Настройка проекта
- ⬜ Базовый Telegram бот (aiogram)
- ⬜ Поддержка Instagram (yt-dlp)
- ⬜ Поддержка YouTube
- ⬜ Поддержка TikTok
- ⬜ Отправка видео/фото
- ⬜ Базовая обработка ошибок

### Phase 2: Улучшения (1 неделя)
- ⬜ Поддержка карусели/альбомов
- ⬜ Извлечение текста поста
- ⬜ Поддержка Twitter
- ⬜ Поддержка VK
- ⬜ Улучшенная обработка ошибок
- ⬜ Логирование

### Phase 3: Полировка (1 неделя)
- ⬜ Сжатие больших файлов
- ⬜ Конвертация форматов
- ⬜ Прогресс-бар загрузки
- ⬜ Кэширование
- ⬜ Статистика использования

### Phase 4: Продакшн (1 неделя)
- ⬜ Docker контейнеризация
- ⬜ Деплой на VPS
- ⬜ Мониторинг
- ⬜ Резервное копирование
- ⬜ Документация

---

## 🎨 UX/UI

### Команды бота

```
/start - Начать работу
/help - Помощь и примеры
/stats - Статистика (опционально)
/about - О боте
```

### Примеры взаимодействия

**Сценарий 1: Скачивание видео из Instagram**

```
Пользователь: https://www.instagram.com/p/ABC123/

Бот: 🔍 Анализирую ссылку...
     ✅ Instagram Reel обнаружен
     ⬇️ Скачиваю видео...
     📤 Отправляю...

Бот: [Видео]
     📝 Описание поста
     👤 Автор: @username
     📅 Дата: 15.12.2024
```

**Сценарий 2: Скачивание карусели**

```
Пользователь: https://www.instagram.com/p/CAROUSEL/

Бот: 🔍 Анализирую ссылку...
     ✅ Instagram пост с 5 фото
     ⬇️ Скачиваю медиа...
     📤 Отправляю...

Бот: [Album: 5 photos]
     📝 Описание поста
```

**Сценарий 3: Ошибка**

```
Пользователь: https://invalid-link

Бот: ❌ Не удалось распознать ссылку

     Поддерживаемые платформы:
     • Instagram
     • YouTube
     • TikTok
     • Twitter

     Используйте /help для примеров
```

---

## 🧪 Тестирование

### Unit тесты
- Парсинг URL
- Определение платформы
- Извлечение ID
- Валидация

### Integration тесты
- Скачивание с реальных URL
- Отправка в Telegram
- Обработка ошибок

### E2E тесты
- Полный цикл: ссылка → скачивание → отправка

---

## 📊 Метрики успеха

### MVP
- ✅ Работает с Instagram, YouTube, TikTok
- ✅ Скачивает видео до 50MB
- ✅ Отправляет с текстом поста
- ✅ Обрабатывает ошибки

### Продакшн
- 99% uptime
- <10 секунд на скачивание
- Поддержка 1000+ пользователей
- 0 критических багов

---

## 🔧 Конфигурация

### Переменные окружения (.env)

```env
# Telegram Bot
BOT_TOKEN=8511650801:AAEGVXeNJeHHhl-ryB8qvQ0dTLTNse-IDK0
BOT_USERNAME=UspSocDownloader_bot

# Paths
TEMP_DIR=./data/temp
LOGS_DIR=./logs

# Limits
MAX_FILE_SIZE=52428800  # 50MB
MAX_VIDEO_DURATION=600  # 10 minutes
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_PERIOD=60    # seconds

# Features
ENABLE_CACHE=true
ENABLE_STATS=true
ENABLE_WATERMARK=false

# yt-dlp
YTDL_FORMAT=best[ext=mp4][height<=1080]
YTDL_OUTPUT_TEMPLATE=%(id)s.%(ext)s

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 📝 Зависимости

### Production (requirements.txt)

```txt
# Telegram Bot
aiogram==3.15.0
aiohttp==3.11.11
aiofiles==24.1.0

# Downloaders
yt-dlp==2024.12.13
gallery-dl==1.28.1

# Media Processing
Pillow==11.0.0
ffmpeg-python==0.2.0

# Utils
python-dotenv==1.0.1
validators==0.34.0
```

### Development (requirements-dev.txt)

```txt
-r requirements.txt

# Testing
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-cov==6.0.0
pytest-mock==3.14.0

# Linting
black==24.10.0
flake8==7.1.1
mypy==1.14.1
isort==5.13.2

# Tools
ipython==8.31.0
```

---

## 🚨 Известные ограничения

### Технические
1. **Instagram:** Требует cookies для приватных аккаунтов
2. **YouTube:** Ограничение на авторские видео
3. **TikTok:** Возможны блокировки по IP
4. **Telegram:** Максимум 50MB на файл

### Юридические
1. Контент защищен авторским правом
2. Использование только для личных целей
3. Не для коммерческого распространения

---

## 📞 Поддержка

### Документация
- README.md - Основная информация
- API.md - API документация
- DEPLOYMENT.md - Инструкции по деплою

### Контакты
- GitHub Issues для багов
- Telegram канал для обновлений

---

## 🗺️ Roadmap

### v1.0 (MVP)
- Instagram, YouTube, TikTok
- Базовое скачивание
- Текст поста

### v1.1
- Twitter, VK, Facebook
- Карусели/альбомы
- Кэширование

### v1.2
- Прогресс-бар
- Статистика
- Admin panel

### v2.0
- Поддержка плейлистов
- Bulk download
- Scheduled downloads
- Premium features

---

**Дата создания:** 04.12.2025
**Автор:** DevTools + Claude Code
**Версия:** 1.0
