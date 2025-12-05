#!/bin/bash
# Быстрый скрипт для обновления бота на сервере

set -e

BOT_DIR="/opt/uspsocdowloader"
BOT_USER="uspbot"
BOT_SERVICE="uspsocdowloader"

echo "🔄 Обновляем UspSocDownloader..."

# Переходим в директорию бота
cd "$BOT_DIR"

# Останавливаем бот
echo "⏹️ Останавливаем бот..."
systemctl stop "$BOT_SERVICE" || true

# Обновляем код
echo "📥 Обновляем код..."
sudo -u "$BOT_USER" git pull origin master

# Обновляем зависимости
echo "📦 Обновляем зависимости..."
sudo -u "$BOT_USER" .venv/bin/pip install -r requirements.txt --upgrade

# Запускаем бот
echo "▶️ Запускаем бот..."
systemctl start "$BOT_SERVICE"

# Проверяем статус
sleep 2
systemctl status "$BOT_SERVICE"

echo "✅ Обновление завершено!"
