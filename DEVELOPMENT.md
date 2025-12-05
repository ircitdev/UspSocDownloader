# UspSocDownloader - Development Guide

## 📋 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Локальная разработка](#локальная-разработка)
3. [Развертывание на сервер](#развертывание-на-сервер)
4. [Структура проекта](#структура-проекта)
5. [Тестирование](#тестирование)
6. [Troubleshooting](#troubleshooting)

---

## 🚀 Быстрый старт

### На локальной машине

```bash
# 1. Клонируем репозиторий
git clone https://github.com/ircitdev/UspSocDownloader.git
cd UspSocDownloader

# 2. Создаем виртуальное окружение
python -m venv .venv

# 3. Активируем окружение
# На Windows:
.venv\Scripts\activate
# На Linux/macOS:
source .venv/bin/activate

# 4. Устанавливаем зависимости
pip install -r requirements.txt

# 5. Создаем .env файл
echo "BOT_TOKEN=YOUR_BOT_TOKEN_HERE" > .env
echo "APP_NAME=UspSocDownloader" >> .env
echo "LOG_LEVEL=INFO" >> .env
echo "DEBUG=True" >> .env

# 6. Запускаем бот
python run_bot.py
```

---

## 💻 Локальная разработка

### Структура проекта

```
UspSocDownloader/
├── src/
│   ├── main.py                 # Entry point
│   ├── bot.py                  # Telegram bot initialization
│   ├── config.py               # Configuration
│   ├── handlers/
│   │   ├── start.py            # /start command
│   │   ├── help.py             # /help command
│   │   ├── url_handler.py      # URL detection
│   │   └── download_handler.py # Download processing
│   ├── processors/
│   │   └── url_processor.py    # Platform detection
│   ├── downloaders/
│   │   └── media_downloader.py # Media downloading
│   ├── utils/
│   │   ├── validators.py       # URL validators
│   │   └── logger.py           # Logging setup
│   └── localization/
│       ├── messages.py         # Russian translations
│       └── __init__.py
├── tests/
│   ├── test_url_processor.py
│   └── test_media_downloader.py
├── docs/
│   ├── DAY_3-4_URL_PROCESSING.md
│   └── DAY_5-7_MEDIA_DOWNLOAD.md
├── deploy/
│   ├── setup_server.sh         # Initial server setup
│   └── update_bot.sh           # Update existing bot
├── requirements.txt            # Dependencies
├── .env                        # Environment (local only)
├── .gitignore                  # Git ignore rules
└── README.md                   # Project readme
```

### Запуск тестов

```bash
# Все тесты
python -m pytest tests/ -v

# Конкретный тест файл
python -m pytest tests/test_url_processor.py -v

# С покрытием
python -m pytest tests/ --cov=src
```

### Развитие функционала

1. **Добавить новую команду:**
   - Создать файл в `src/handlers/new_command.py`
   - Зарегистрировать router в `src/bot.py`

2. **Добавить новую платформу:**
   - Добавить validator в `src/utils/validators.py`
   - Добавить ID extractor в `src/processors/url_processor.py`
   - Добавить yt-dlp конфиг в `src/downloaders/media_downloader.py`
   - Добавить локализацию в `src/localization/messages.py`
   - Написать тесты

3. **Добавить локализацию:**
   - Создать файл `src/localization/messages_XX.py` (XX - код языка)
   - Добавить поддержку выбора языка в конфигурацию

---

## 🌐 Развертывание на сервер

### Автоматическое развертывание

```bash
# На локальной машине, в терминале:

# 1. Установить SSH ключ (если еще не установлен)
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. Добавить публичный ключ на сервер
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@31.44.7.144

# 3. Подключиться к серверу
ssh root@31.44.7.144

# На сервере:

# 4. Скачать и запустить скрипт установки
cd /tmp
wget https://raw.githubusercontent.com/ircitdev/UspSocDownloader/master/deploy/setup_server.sh
chmod +x setup_server.sh

# 5. Установить переменную окружения с URL репозитория
export REPO_URL="https://github.com/ircitdev/UspSocDownloader.git"

# 6. Запустить установку
./setup_server.sh
```

### Ручное развертывание

```bash
# На сервере:

# 1. Установить зависимости
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv git ffmpeg

# 2. Создать пользователя для бота
sudo useradd -m -s /bin/bash uspbot

# 3. Клонировать репозиторий
sudo -u uspbot git clone https://github.com/ircitdev/UspSocDownloader.git /opt/uspsocdowloader
cd /opt/uspsocdowloader

# 4. Создать виртуальное окружение
sudo -u uspbot python3.11 -m venv .venv
sudo -u uspbot .venv/bin/pip install -r requirements.txt

# 5. Создать .env файл
sudo bash -c 'cat > /opt/uspsocdowloader/.env << EOF
BOT_TOKEN=8511650801:AAEGVXeNJeHHhl-ryB8qvQ0dTLTNse-IDK0
APP_NAME=UspSocDownloader
LOG_LEVEL=INFO
DEBUG=False
EOF'

# 6. Создать systemd сервис (см. deploy/setup_server.sh)
```

### Управление ботом на сервере

```bash
# Запустить бот
sudo systemctl start uspsocdowloader

# Остановить бот
sudo systemctl stop uspsocdowloader

# Перезагрузить бот
sudo systemctl restart uspsocdowloader

# Проверить статус
sudo systemctl status uspsocdowloader

# Просмотреть логи (последние 50 строк)
sudo journalctl -u uspsocdowloader -n 50

# Следить за логами в реальном времени
sudo journalctl -u uspsocdowloader -f

# Включить автозапуск
sudo systemctl enable uspsocdowloader

# Отключить автозапуск
sudo systemctl disable uspsocdowloader
```

### Обновление бота на сервере

```bash
# Вариант 1: Использовать скрипт обновления
ssh root@31.44.7.144 'bash /opt/uspsocdowloader/deploy/update_bot.sh'

# Вариант 2: Вручную
ssh root@31.44.7.144
cd /opt/uspsocdowloader
sudo systemctl stop uspsocdowloader
sudo -u uspbot git pull origin master
sudo -u uspbot .venv/bin/pip install -r requirements.txt --upgrade
sudo systemctl start uspsocdowloader
```

---

## 🧪 Тестирование

### Настройка тестирования

```bash
# Установить зависимости для тестирования
pip install pytest pytest-cov pytest-asyncio

# Запустить тесты
pytest tests/ -v

# С покрытием кода
pytest tests/ --cov=src --cov-report=html
```

### Структура тестов

- `tests/test_url_processor.py` - Тесты обработки URL (35 тестов)
- `tests/test_media_downloader.py` - Тесты загрузки медиа (16 тестов)

### Написание новых тестов

```python
import pytest
from src.processors.url_processor import URLProcessor

@pytest.mark.asyncio
async def test_new_feature():
    processor = URLProcessor()
    result = await processor.detect_platform("https://example.com/video")
    assert result.is_valid
```

---

## 🐛 Troubleshooting

### Проблема: SSL ошибка при запуске бота

```
SSL: APPLICATION_DATA_AFTER_CLOSE_NOTIFY
```

**Решение:**

```bash
# Обновить aiogram и зависимости
pip install --upgrade aiogram httpx
```

### Проблема: FFmpeg не найден

```
FileNotFoundError: ffmpeg not found
```

**Решение:**

```bash
# Windows (через choco)
choco install ffmpeg

# Linux
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Проблема: BOT_TOKEN не установлен

```
ValueError: BOT_TOKEN not set
```

**Решение:**

1. Создать `.env` файл в корне проекта
2. Добавить: `BOT_TOKEN=YOUR_BOT_TOKEN_HERE`
3. Получить токен у @BotFather в Telegram

### Проблема: Ошибка подключения к серверу

```
[Errno 111] Connection refused
```

**Проверить:**

```bash
# Проверить доступность сервера
ping 31.44.7.144

# Проверить SSH доступ
ssh -v root@31.44.7.144

# Проверить firewall
sudo ufw status

# Если нужно открыть порт
sudo ufw allow 22
```

### Проблема: Файл слишком большой

```
Exception: File size (XXX MB) exceeds limit
```

**Решение:** Увеличить лимит в `src/config.py`

```python
FILE_SIZE_LIMITS = {
    'video': 150 * 1024 * 1024,  # 150 MB instead of 100 MB
    'audio': 75 * 1024 * 1024,   # 75 MB instead of 50 MB
    'photo': 15 * 1024 * 1024,   # 15 MB instead of 10 MB
}
```

---

## 📞 Контакты

- GitHub: <https://github.com/ircitdev/UspSocDownloader>
- Issues: <https://github.com/ircitdev/UspSocDownloader/issues>
- Telegram Bot: @UspSocDownloader_bot

---

**Последнее обновление:** 04.12.2025
