# UspSocDownloader

> Telegram-бот для скачивания контента из социальных сетей с AI-функциями

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.15-green)](https://docs.aiogram.dev/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-orange)](https://openai.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

Telegram-бот для скачивания видео, фото и каруселей из Instagram, YouTube, TikTok, Twitter/X и VK. Включает AI-функции: перевод, рерайт текста и OCR с изображений.

---

## Telegram Bot

- **Bot:** [@UspSocDownloader_bot](https://t.me/UspSocDownloader_bot)
- **Server:** VPS 31.44.7.144
- **Status:** Production

---

## Возможности

### Поддерживаемые платформы

| Платформа | Видео | Фото | Карусели | Reels/Shorts | Multi-Video |
|-----------|-------|------|----------|--------------|-------------|
| Instagram | Yes | Yes | Yes | Yes | - |
| YouTube | Yes | - | - | Yes (Shorts) | - |
| TikTok | Yes | - | - | - | - |
| Twitter/X | Yes | Yes | Yes | - | Yes |
| VK | Yes | - | - | Yes (Clips) | - |

### Функционал скачивания

- Скачивание видео (до 1080p)
- Скачивание фото (оригинальное качество)
- Поддержка каруселей/альбомов (до 10 медиа)
- Twitter/X multi-video твиты (несколько видео в одном посте)
- YouTube: выбор качества + скачивание только аудио (MP3)
- Извлечение текста поста
- Информация об авторе (username, ссылка)
- Метаданные (лайки, комментарии, просмотры)

### AI-функции (OpenAI GPT-4)

| Функция | Описание | Модель |
|---------|----------|--------|
| Перевод | Автоматический перевод на русский | gpt-4o-mini |
| Рерайт | 3 стиля: экспертный, юмористический, дружелюбный | gpt-4o-mini |
| OCR | Извлечение текста с изображений | gpt-4o (vision) |

---

## Архитектура

```
UspSocDownloader/
├── src/
│   ├── main.py                 # Entry point
│   ├── bot.py                  # Bot initialization
│   ├── config.py               # Configuration
│   │
│   ├── handlers/
│   │   ├── start.py            # /start command
│   │   ├── help.py             # /help command
│   │   └── url_handler.py      # URL processing + callbacks
│   │
│   ├── downloaders/
│   │   └── media_downloader.py # yt-dlp + gallery-dl downloader
│   │
│   ├── processors/
│   │   └── url_processor.py    # URL parsing & validation
│   │
│   ├── utils/
│   │   ├── logger.py           # Logging
│   │   ├── validators.py       # Input validation
│   │   └── translator.py       # OpenAI: translate, rewrite, OCR
│   │
│   └── localization/
│       └── messages.py         # UI messages (Russian)
│
├── data/
│   ├── downloads/              # Temporary downloads
│   │   ├── video/
│   │   ├── photo/
│   │   └── audio/
│   └── cookies/                # Platform cookies
│       └── instagram_cookies.txt
│
├── logs/                       # Application logs
├── tests/                      # Unit & integration tests
└── run_bot.py                  # Production entry point
```

---

## Технологии

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Framework | aiogram | 3.15 |
| Downloader | yt-dlp | latest |
| Instagram photos | gallery-dl | latest |
| AI | OpenAI API | GPT-4o |
| HTTP | aiohttp | 3.x |
| Runtime | Python | 3.11+ |

---

## Установка

### Требования

- Python 3.11+
- yt-dlp
- gallery-dl
- FFmpeg (для видео)

### Локальная установка

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/UspSocDownloader.git
cd UspSocDownloader

# Создать virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate   # Windows

# Установить зависимости
pip install -r requirements.txt

# Создать .env файл
cp .env.example .env
# Отредактировать .env с вашими токенами
```

### Конфигурация (.env)

```env
BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
LOG_LEVEL=INFO
```

### Запуск

```bash
# Локально
python run_bot.py

# Или через systemd (production)
systemctl start uspsocdowloader
```

---

## Деплой на VPS

### Systemd service

```ini
# /etc/systemd/system/uspsocdowloader.service
[Unit]
Description=UspSocDownloader Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/uspsocdowloader
ExecStart=/opt/uspsocdowloader/.venv/bin/python run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Управление

```bash
# Запуск
systemctl start uspsocdowloader

# Остановка
systemctl stop uspsocdowloader

# Перезапуск
systemctl restart uspsocdowloader

# Логи
journalctl -u uspsocdowloader -f
```

---

## Использование

### Скачивание контента

Просто отправьте ссылку боту:

```
https://www.instagram.com/p/ABC123/
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.tiktok.com/@user/video/123456
https://twitter.com/user/status/123456
https://vk.com/video-123_456
```

### AI-функции

После скачивания появляются интерактивные кнопки:

1. **Перевести на русский** - для иностранного текста
2. **Сделать рерайт** - выбор из 3 стилей
3. **Получить текст с картинок** - OCR для каруселей с текстом

---

## API Reference

### URL Handler Callbacks

| Callback | Описание |
|----------|----------|
| `translate` | Перевод текста на русский |
| `rewrite_menu` | Меню выбора стиля рерайта |
| `rewrite_expert` | Рерайт в экспертном стиле |
| `rewrite_humor` | Рерайт в юмористическом стиле |
| `rewrite_friendly` | Рерайт в дружелюбном стиле |
| `ocr_extract` | Извлечение текста с изображений |

### Translator Functions

```python
# Перевод
await translate_to_russian(text: str) -> str

# Рерайт
await rewrite_text(text: str, style: str) -> str
# style: "expert" | "humor" | "friendly"

# OCR
await extract_text_from_images(image_paths: List[str]) -> str

# Проверка текста на изображениях
await check_images_have_text(image_paths: List[str]) -> bool
```

---

## Разработка

### Тестирование

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src

# Только unit тесты
pytest tests/unit/
```

### Линтинг

```bash
# Format
black src tests

# Lint
flake8 src tests

# Type check
mypy src
```

---

## Changelog

### v1.2.0 (2025-12-07)

- Twitter/X: поддержка multi-video твитов (несколько видео в одном посте)
- Twitter/X: полный текст твита без обрезания
- VK: улучшенная обработка ошибок для постов без видео
- YouTube: выбор качества видео (360p-1080p)
- YouTube: скачивание только аудио (MP3)
- Уведомления в супергруппу с топиками для каждого пользователя

### v1.1.0 (2025-11-22)

- Google Sheets интеграция для статистики
- Уведомления администраторам
- Улучшенная обработка Instagram каруселей
- Реферальная система

### v1.0.0 (2024-12-07)

- Instagram: видео, фото, карусели, reels
- YouTube: видео, shorts
- TikTok: видео без водяного знака
- Twitter/X: видео, фото
- VK: видео, клипы
- AI: перевод на русский (GPT-4o-mini)
- AI: рерайт в 3 стилях (GPT-4o-mini)
- AI: OCR с изображений (GPT-4o vision)
- Интерактивные inline-кнопки

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Disclaimer

Этот бот предназначен только для личного использования. Уважайте авторские права и условия использования платформ социальных сетей.

---

**Powered by Claude Code**
