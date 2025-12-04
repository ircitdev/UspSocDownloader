# 🚀 Быстрый старт - Запуск бота за 30 секунд

## 1️⃣ Откройте терминал в проекте

```powershell
cd D:\DevTools\Database\UspSocDownloader
```

## 2️⃣ Запустите бота

```powershell
python src/main.py
```

**Вы должны увидеть:**

```
2025-12-04 XX:XX:XX,XXX - bot - INFO - Starting UspSocDownloader
2025-12-04 XX:XX:XX,XXX - bot - INFO - Starting bot polling...
```

**Бот готов!** Оставьте терминал открытым.

## 3️⃣ Откройте Telegram

Найдите: **@UspSocDownloader_bot**

## 4️⃣ Тестируйте команды

### Отправьте `/start`

```
👋 Welcome to UspSocDownloader!

🚀 I can help you download media from social networks:
• Instagram (posts, reels, stories)
• YouTube (videos, shorts)
• TikTok (videos)

📝 Just send me a link and I'll download it for you!

❓ Type /help for more information.
```

### Отправьте `/help`

```
❓ Help - UspSocDownloader

🎯 How to use:
1️⃣ Send me a link from a social network
2️⃣ I'll analyze and download the media
3️⃣ You'll receive the file with description

... (и дальше справка)
```

## ✅ Готово

Бот работает и отвечает на команды.

---

## 🛑 Остановка

В терминале нажмите: `Ctrl+C`

---

## ❓ Проблемы?

### Бот не запускается

Проверьте `.env`:

```powershell
Get-Content .env | grep BOT_TOKEN
```

Должно быть значение с токеном.

### Бот не отвечает в Telegram

1. Убедитесь что терминал работает (видите `Starting bot polling...`)
2. Найдите правильного бота: **@UspSocDownloader_bot**
3. Проверьте интернет соединение

---

## 📚 Для большей информации

- [RUN_BOT.md](RUN_BOT.md) - подробная инструкция
- [BOT_SETUP_COMPLETE.md](BOT_SETUP_COMPLETE.md) - что было создано
- [BOT_FINAL_REPORT.md](BOT_FINAL_REPORT.md) - итоговый отчет

---

**That's it! Ваш Telegram бот работает! 🎉**
