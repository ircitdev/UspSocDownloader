# UspSocDownloader

> 🤖 Telegram бот для скачивания контента из социальных сетей

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.15-green)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

Telegram бот который скачивает видео, фото и карусели из Instagram, YouTube, TikTok и других популярных социальных сетей вместе с текстом поста.

---

## 📱 Telegram Bot

- **Bot:** [@UspSocDownloader_bot](https://t.me/UspSocDownloader_bot)
- **Статус:** 🚧 В разработке (MVP)
- **API Token:** Хранится в `.env`

---

## ✨ Возможности

### Поддерживаемые платформы:

- ✅ **Instagram** - посты, reels, IGTV, stories
- ✅ **YouTube** - видео, shorts
- ✅ **TikTok** - видео без водяного знака
- ⬜ **Twitter/X** - в планах
- ⬜ **VK** - в планах
- ⬜ **Facebook** - в планах

### Функционал:

- 📥 Скачивание видео (до 1080p)
- 🖼️ Скачивание фото (оригинальное качество)
- 🎠 Поддержка каруселей/альбомов
- 📝 Извлечение текста поста
- 👤 Информация об авторе
- 📊 Метаданные (дата, лайки, просмотры)

---

## 🚀 Быстрый старт

### 1. Клонировать проект

```powershell
cd D:\DevTools\Database\UspSocDownloader
```

### 2. Активировать virtual environment

```powershell
.\.venv\Scripts\activate.ps1
```

### 3. Установить зависимости

```bash
pip install -r requirements-dev.txt
```

### 4. Создать .env файл

```env
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=YourBot_bot
LOG_LEVEL=INFO
TEMP_DIR=./data/temp
```

### 5. Запустить бота

```bash
python src/main.py
```

---

## 📚 Документация

### Основная:
- **[QUICK_START.md](QUICK_START.md)** - Быстрый старт для разработчиков
- **[PROJECT_SPEC.md](PROJECT_SPEC.md)** - Полное техническое задание
- **[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)** - Детальный план разработки

### Для пользователей:
- **[USER_GUIDE.md](USER_GUIDE.md)** - Руководство пользователя (TODO)
- **[FAQ.md](FAQ.md)** - Часто задаваемые вопросы (TODO)

---

## 🏗️ Архитектура

```
UspSocDownloader/
├── src/
│   ├── main.py              # Entry point
│   ├── bot.py               # Bot initialization
│   ├── config.py            # Configuration
│   │
│   ├── handlers/            # Command & message handlers
│   │   ├── start.py
│   │   ├── help.py
│   │   └── url_handler.py
│   │
│   ├── downloaders/         # Platform-specific downloaders
│   │   ├── instagram.py
│   │   ├── youtube.py
│   │   └── tiktok.py
│   │
│   ├── processors/          # Data processing
│   │   ├── url_processor.py
│   │   └── media_processor.py
│   │
│   └── utils/               # Utilities
│       ├── logger.py
│       └── file_utils.py
│
├── tests/                   # Unit & integration tests
├── data/                    # Temporary files
└── logs/                    # Log files
```

---

## 🛠️ Технологии

- **Python 3.11+**
- **aiogram 3.15** - Telegram Bot framework
- **yt-dlp** - Universal media downloader
- **aiohttp** - Async HTTP client
- **python-dotenv** - Environment management

---

## 🧪 Testing

```bash
# Запустить все тесты
pytest

# С покрытием
pytest --cov=src

# Только unit тесты
pytest tests/unit/

# Только integration тесты
pytest tests/integration/
```

---

## 🔧 Development

### Форматирование и линтинг:

```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type check
mypy src
```

### Pre-commit hooks (рекомендуется):

```bash
pip install pre-commit
pre-commit install
```

---

## 📝 Usage Examples

### Скачивание из Instagram:

```
Пользователь: https://www.instagram.com/p/ABC123/

Бот: 🔍 Анализирую ссылку...
     ✅ Instagram Reel обнаружен
     ⬇️ Скачиваю видео...
     📤 Отправляю...

Бот: [Видео]
     📝 Описание поста
     👤 Автор: @username
     📅 15.12.2024
```

### Скачивание с YouTube:

```
Пользователь: https://www.youtube.com/watch?v=dQw4w9WgXcQ

Бот: 🔍 Анализирую ссылку...
     ✅ YouTube видео обнаружено
     ⬇️ Скачиваю...
     📤 Отправляю...

Бот: [Видео]
     📝 Never Gonna Give You Up
     👤 Rick Astley
```

---

## 🚧 Roadmap

### Phase 1: MVP (Недели 1-2)
- [x] Создать проект
- [x] Написать ТЗ и план
- [ ] Базовый Telegram бот
- [ ] Instagram support
- [ ] YouTube support
- [ ] TikTok support

### Phase 2: Улучшения (Неделя 3)
- [ ] Twitter/X support
- [ ] VK support
- [ ] Карусели/альбомы
- [ ] Кэширование

### Phase 3: Полировка (Неделя 4)
- [ ] Сжатие файлов
- [ ] Прогресс-бар
- [ ] Статистика

### Phase 4: Продакшн (Неделя 5)
- [ ] Docker
- [ ] Деплой на VPS
- [ ] Мониторинг
- [ ] Документация

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

Этот бот предназначен только для личного использования. Пожалуйста, уважайте авторские права и условия использования платформ социальных сетей.

---

## 📞 Support

- 📧 Email: support@uspsocdownloader.bot (TODO)
- 💬 Telegram: @UspSocDownloader_support (TODO)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/UspSocDownloader/issues)

---

## 🙏 Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Telegram Bot framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Media downloader
- [DevTools](https://github.com/ircitdev/devtools) - Development environment

---

**Created with DevTools Python Project Generator**
**Powered by Claude Code**

---

## 📊 Stats

- ⭐ **Stars:** 0
- 🍴 **Forks:** 0
- 👥 **Contributors:** 1
- 📦 **Version:** 0.1.0 (MVP in development)
