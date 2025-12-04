# UspSocDownloader - Быстрый старт

## 🚀 Краткая информация

**Проект:** Telegram бот для скачивания контента из социальных сетей
**Telegram Bot:** @UspSocDownloader_bot
**API Token:** `8511650801:AAEGVXeNJeHHhl-ryB8qvQ0dTLTNse-IDK0`

---

## 📦 Что нужно сделать

### MVP (2 недели):
1. ✅ Создать базовый Telegram бот (aiogram)
2. ✅ Добавить поддержку Instagram (yt-dlp)
3. ✅ Добавить поддержку YouTube
4. ✅ Добавить поддержку TikTok
5. ✅ Отправлять видео/фото пользователю
6. ✅ Добавить текст поста

### Как работает:
```
Пользователь → Отправляет ссылку
             ↓
Бот → Определяет платформу (Instagram/YouTube/TikTok)
    ↓
Бот → Скачивает контент (yt-dlp)
    ↓
Бот → Отправляет файл + описание
```

---

## 🛠️ Технологии

- **Python 3.11+**
- **aiogram 3.15** - Telegram Bot framework
- **yt-dlp** - Загрузчик (Instagram, YouTube, TikTok, и др.)
- **aiohttp** - Async HTTP
- **python-dotenv** - Конфигурация

---

## 📁 Структура проекта

```
UspSocDownloader/
├── src/
│   ├── main.py              # Entry point
│   ├── bot.py               # Bot инициализация
│   ├── config.py            # Конфигурация
│   │
│   ├── handlers/
│   │   ├── start.py         # /start команда
│   │   ├── help.py          # /help команда
│   │   └── url_handler.py   # Обработка ссылок
│   │
│   ├── downloaders/
│   │   ├── base.py          # Базовый downloader
│   │   ├── instagram.py     # Instagram
│   │   ├── youtube.py       # YouTube
│   │   └── tiktok.py        # TikTok
│   │
│   ├── processors/
│   │   └── url_processor.py # Парсинг URL
│   │
│   └── utils/
│       ├── logger.py        # Логирование
│       └── file_utils.py    # Работа с файлами
│
├── data/                    # Временные файлы
├── logs/                    # Логи
├── .env                     # Секреты (НЕ в Git!)
└── requirements.txt         # Зависимости
```

---

## 🎯 Первые шаги (День 1-2)

### 1. Обновить зависимости

**requirements.txt:**
```txt
aiogram==3.15.0
yt-dlp==2024.12.13
aiohttp==3.11.11
aiofiles==24.1.0
python-dotenv==1.0.1
```

### 2. Создать .env файл

**.env:**
```env
BOT_TOKEN=8511650801:AAEGVXeNJeHHhl-ryB8qvQ0dTLTNse-IDK0
BOT_USERNAME=UspSocDownloader_bot
LOG_LEVEL=INFO
TEMP_DIR=./data/temp
```

### 3. Создать базовый бот

**src/main.py:**
```python
import asyncio
from bot import bot, dp
from handlers import start, help, url_handler
from utils.logger import setup_logger

async def main():
    logger = setup_logger()
    logger.info("Starting bot...")

    # Регистрация handlers
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(url_handler.router)

    # Запуск
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Запустить бота

```bash
# Активировать venv
.\.venv\Scripts\activate.ps1

# Установить зависимости
pip install -r requirements.txt

# Запустить
python src/main.py
```

---

## 📝 Приоритет задач

### Неделя 1:
- [x] Создать проект
- [ ] Настроить базовый бот ← **НАЧАТЬ С ЭТОГО**
- [ ] Добавить /start и /help
- [ ] Определение платформы по URL
- [ ] Instagram downloader
- [ ] Отправка видео в Telegram

### Неделя 2:
- [ ] YouTube downloader
- [ ] TikTok downloader
- [ ] Извлечение текста поста
- [ ] Обработка ошибок
- [ ] Тестирование

---

## 💡 Полезные ссылки

### Документация:
- [aiogram 3.x](https://docs.aiogram.dev/en/latest/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Примеры:
- [aiogram примеры](https://github.com/aiogram/aiogram/tree/dev-3.x/examples)
- [yt-dlp примеры](https://github.com/yt-dlp/yt-dlp#usage-and-options)

### Детальная документация:
- [PROJECT_SPEC.md](PROJECT_SPEC.md) - Полное ТЗ
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) - План разработки

---

## 🧪 Тестовые ссылки

### Instagram:
```
https://www.instagram.com/p/ABC123/
https://www.instagram.com/reel/XYZ789/
```

### YouTube:
```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/dQw4w9WgXcQ
```

### TikTok:
```
https://www.tiktok.com/@username/video/1234567890
```

---

## ⚡ Следующий шаг

**Откройте проект в VS Code:**
```powershell
cd D:\DevTools\Database\UspSocDownloader
code .
```

**Используйте Claude Code:**
- В Claude Code введите: "Помоги создать базовый Telegram бот с aiogram"
- Или используйте slash команды: `/analyze`, `/document`, `/test`

**Начните разработку с Day 1-2 задач из DEVELOPMENT_PLAN.md**

---

🎯 **Цель на сегодня:** Базовый бот отвечающий на /start и /help

🚀 **Удачи в разработке!**
