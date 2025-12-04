# 🚀 Запуск Telegram Бота

## ⚡ Быстрый старт

```powershell
cd D:\DevTools\Database\UspSocDownloader
python src/main.py
```

**Готово!** Бот запущен и слушает команды из Telegram.

---

## 📱 Тестирование в Telegram

### 1. Откройте Telegram

Найдите бота: **@UspSocDownloader_bot**

### 2. Отправьте команду `/start`

**Ожидаемый ответ:**

```
👋 Welcome to UspSocDownloader!

🚀 I can help you download media from social networks:
• Instagram (posts, reels, stories)
• YouTube (videos, shorts)
• TikTok (videos)

📝 Just send me a link and I'll download it for you!

❓ Type /help for more information.
```

### 3. Отправьте команду `/help`

**Ожидаемый ответ:**

```
❓ Help - UspSocDownloader

🎯 How to use:
1️⃣ Send me a link from a social network
2️⃣ I'll analyze and download the media
3️⃣ You'll receive the file with description

📱 Supported platforms:
• Instagram - posts, reels, stories
• YouTube - videos, shorts, playlists
• TikTok - videos (without watermark)

... и дальше справка
```

---

## 🔍 Консольный вывод

Пока бот работает, в консоли вы увидите логи:

```
2025-12-04 20:42:59,XXX - bot - INFO - Starting UspSocDownloader
2025-12-04 20:42:59,XXX - bot - INFO - Creating bot instance - UspSocDownloader
2025-12-04 20:42:59,XXX - bot - INFO - Bot commands configured
2025-12-04 20:42:59,XXX - bot - INFO - Bot and dispatcher created successfully
2025-12-04 20:42:59,XXX - bot - INFO - Starting bot polling...
2025-12-04 20:42:59,XXX - src.handlers.start - INFO - User 123456789 started bot
2025-12-04 20:42:59,XXX - src.handlers.start - INFO - Welcome message sent to 123456789
```

### Логи сохраняются

Все события записываются в `logs/bot.log`:

```powershell
Get-Content logs/bot.log -Tail 50
```

---

## 🛑 Остановка бота

Нажмите в терминале: **`Ctrl+C`**

```
^C2025-12-04 20:45:00,XXX - __main__ - INFO - Bot interrupted by user
2025-12-04 20:45:00,XXX - bot - INFO - Closing bot session
```

---

## 🧪 Без Telegram: Локальное тестирование

Если нет доступа к Telegram или хотите быстро проверить обработчики:

```powershell
# Тестировать хендлеры локально
python test_handlers.py
```

**Вывод:**

```
[PASS] /start handler
[PASS] /help handler
[SUCCESS] All handler tests passed!
```

---

## ❓ Проблемы?

### Бот не отвечает

1. **Проверьте логи:**

   ```powershell
   Get-Content logs/bot.log -Last 20
   ```

2. **Убедитесь что бот запущен:**

   ```powershell
   python src/main.py
   ```

   Должно быть `Starting bot polling...`

3. **Проверьте интернет соединение**

### Ошибка: "BOT_TOKEN not found"

Проверьте `.env` файл:

```powershell
Get-Content .env
```

Должно быть:

```
BOT_TOKEN=8511650801:AAEGVXeNJeHHhl-ryB8qvQ0dTLTNse-IDK0
```

### Ошибка при импорте aiogram

Установите пакеты:

```powershell
pip install -r requirements.txt
```

---

## 📊 Архитектура

```
Telegram User
    ↓
Bot Polling (слушает обновления)
    ↓
Message Handler Dispatcher
    ├─ Command: /start → start.py → start_command()
    └─ Command: /help  → help.py  → help_command()
    ↓
Logger (console + logs/bot.log)
```

---

## 🔧 Настройки

### Изменить уровень логирования

В `.env` измените:

```env
LOG_LEVEL=DEBUG    # Больше информации
LOG_LEVEL=ERROR    # Только ошибки
```

### Изменить боту сообщение

Отредактируйте:

- `/start` - `src/handlers/start.py`
- `/help` - `src/handlers/help.py`

---

## 📚 Следующее

Когда базовый бот готов, можно добавить:

1. **URL обработчик** - распознавание ссылок
2. **Instagram downloader** - скачивание контента
3. **YouTube downloader**
4. **TikTok downloader**
5. **Отправка файлов в Telegram**

Следуйте плану в [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

---

## 💡 Советы

- Держите бота запущенным в отдельном окне терминала
- Логи помогут при отладке - проверяйте их если что-то не работает
- Можно запустить несколько копий бота с разными токенами
- Используйте `/help` для справки внутри Telegram

---

**Удачи в тестировании! 🚀**
