#!/bin/bash
# Скрипт для развертывания UspSocDownloader на сервере

set -e

echo "🚀 Начинаем развертывание UspSocDownloader на сервере..."

# Переменные
BOT_DIR="/opt/uspsocdowloader"
BOT_USER="uspbot"
BOT_SERVICE="uspsocdowloader"
REPO_URL="${REPO_URL:-https://github.com/ircitdev/UspSocDownloader.git}"

# 1. Обновляем систему
echo "📦 Обновляем пакеты..."
apt-get update
apt-get upgrade -y

# 2. Устанавливаем зависимости
echo "📦 Устанавливаем зависимости..."
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    git \
    ffmpeg \
    curl \
    wget

# 3. Создаем пользователя для бота
echo "👤 Создаем пользователя $BOT_USER..."
if ! id "$BOT_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$BOT_USER"
    echo "✅ Пользователь $BOT_USER создан"
else
    echo "✅ Пользователь $BOT_USER уже существует"
fi

# 4. Клонируем репозиторий
echo "📥 Клонируем репозиторий..."
if [ -d "$BOT_DIR" ]; then
    echo "📂 Директория $BOT_DIR уже существует, обновляем..."
    cd "$BOT_DIR"
    sudo -u "$BOT_USER" git pull origin master
else
    mkdir -p "$(dirname "$BOT_DIR")"
    sudo -u "$BOT_USER" git clone "$REPO_URL" "$BOT_DIR"
fi

# 5. Устанавливаем виртуальное окружение
echo "🐍 Создаем виртуальное окружение..."
cd "$BOT_DIR"
sudo -u "$BOT_USER" python3.11 -m venv .venv
sudo -u "$BOT_USER" .venv/bin/pip install --upgrade pip setuptools wheel

# 6. Устанавливаем зависимости проекта
echo "📦 Устанавливаем зависимости проекта..."
sudo -u "$BOT_USER" .venv/bin/pip install -r requirements.txt

# 7. Создаем директории для данных
echo "📁 Создаем директории..."
sudo -u "$BOT_USER" mkdir -p "$BOT_DIR/data/videos"
sudo -u "$BOT_USER" mkdir -p "$BOT_DIR/data/audio"
sudo -u "$BOT_USER" mkdir -p "$BOT_DIR/data/photos"
sudo -u "$BOT_USER" mkdir -p "$BOT_DIR/logs"

# 8. Создаем .env файл
echo "⚙️ Создаем конфигурационный файл..."
if [ ! -f "$BOT_DIR/.env" ]; then
    cat > "$BOT_DIR/.env" << EOF
BOT_TOKEN=${BOT_TOKEN:-YOUR_BOT_TOKEN_HERE}
APP_NAME=UspSocDownloader
LOG_LEVEL=INFO
DEBUG=False
EOF
    echo "⚠️  Отредактируйте $BOT_DIR/.env с вашим BOT_TOKEN"
fi

# 9. Создаем systemd сервис
echo "🔧 Создаем systemd сервис..."
cat > "/etc/systemd/system/${BOT_SERVICE}.service" << EOF
[Unit]
Description=UspSocDownloader Telegram Bot
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/.venv/bin"
ExecStart=$BOT_DIR/.venv/bin/python run_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 10. Даем права на логи
chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"
chmod 755 "$BOT_DIR"

# 11. Перезагружаем systemd
systemctl daemon-reload
systemctl enable "$BOT_SERVICE"

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте .env файл с вашим BOT_TOKEN:"
echo "   nano $BOT_DIR/.env"
echo ""
echo "2. Запустите бот:"
echo "   systemctl start $BOT_SERVICE"
echo ""
echo "3. Проверьте статус:"
echo "   systemctl status $BOT_SERVICE"
echo ""
echo "4. Просмотрите логи:"
echo "   journalctl -u $BOT_SERVICE -f"
echo ""
