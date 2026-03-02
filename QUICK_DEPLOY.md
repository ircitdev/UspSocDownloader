# ⚡ Быстрый деплой веб-документации

## 🎯 Что сделано

1. ✅ Создан адаптивный веб-интерфейс (`help/index.html`)
2. ✅ Добавлена команда `/howto` с Telegram Mini App
3. ✅ Настроен Nginx конфиг для поддомена
4. ✅ Создана документация по деплою

## 🚀 Как задеплоить на сервер

### Вариант 1: Автоматический (рекомендуется)

```bash
# 1. SSH на сервер
ssh root@31.44.7.144

# 2. Перейти в директорию проекта
cd /opt/uspsocdowloader

# 3. Скачать изменения
git pull origin master

# 4. Запустить скрипт деплоя
bash DEPLOY_WEB_DOCS.sh
```

Скрипт автоматически:
- Скачает последние изменения
- Настроит permissions
- Создаст Nginx конфигурацию
- Получит SSL сертификат
- Перезапустит Nginx и бот

### Вариант 2: Ручной

```bash
# 1. SSH на сервер
ssh root@31.44.7.144

# 2. Перейти в директорию
cd /opt/uspsocdowloader

# 3. Pull изменений
git pull origin master

# 4. Установить certbot (если нет)
apt update
apt install certbot python3-certbot-nginx -y

# 5. Скопировать Nginx конфиг
cp help/nginx.conf /etc/nginx/sites-available/socdownloader-docs
ln -s /etc/nginx/sites-available/socdownloader-docs /etc/nginx/sites-enabled/

# 6. Проверить конфиг
nginx -t

# 7. Получить SSL сертификат
certbot --nginx -d socdownloader.tools.uspeshnyy.ru

# 8. Reload Nginx
systemctl reload nginx

# 9. Restart бот
systemctl restart uspsocdowloader
```

## ✅ Проверка

### 1. Проверить DNS
```bash
nslookup socdownloader.tools.uspeshnyy.ru
# Должен вернуть: 31.44.7.144
```

### 2. Проверить сайт в браузере
Откройте: https://socdownloader.tools.uspeshnyy.ru

Должна открыться красивая страница с документацией.

### 3. Проверить в Telegram
1. Откройте [@UspSocDownloader_bot](https://t.me/UspSocDownloader_bot)
2. Отправьте: `/howto`
3. Нажмите кнопку "📖 Открыть руководство"
4. Должен открыться Telegram Mini App с документацией

### 4. Проверить логи
```bash
# Bot logs
journalctl -u uspsocdowloader -n 50

# Nginx logs
tail -f /var/log/nginx/socdownloader-docs-access.log
```

## 📱 Команда /howto

После деплоя пользователи смогут:
- Отправить `/howto` боту
- Нажать кнопку "📖 Открыть руководство"
- Откроется полная интерактивная документация прямо в Telegram
- Работает как обычная веб-страница внутри Telegram

## 🎨 Дизайн

- **Цвета**: Тёмно-синяя палитра (#0f1729, #1a2642) с голубым акцентом (#4a9eff)
- **Стиль**: Матовое стекло (glass morphism)
- **Шрифты**:
  - Montserrat Bold для заголовков
  - Roboto Regular для текста
- **Адаптивность**: Работает на всех устройствах
- **Анимации**: Плавные переходы и hover-эффекты

## 📂 Структура файлов

```
help/
├── index.html          # Главная страница (адаптивный интерфейс)
├── nginx.conf          # Конфигурация Nginx
├── DEPLOYMENT.md       # Детальная документация по деплою
```

## 🔧 Возможности веб-интерфейса

- ✅ Быстрая навигация по разделам
- ✅ Копирование команд одним кликом
- ✅ Интерактивный FAQ с раскрывающимися ответами
- ✅ Telegram Web App SDK интеграция
- ✅ Smooth scroll
- ✅ Haptic feedback на мобильных
- ✅ Темная тема с градиентами
- ✅ Анимированные карточки

## 🆘 Troubleshooting

### Проблема: DNS не резолвится
**Решение**: Подождите 5-10 минут для распространения DNS

### Проблема: 502 Bad Gateway
**Решение**:
```bash
ls -la /opt/uspsocdowloader/help/
chmod -R 755 /opt/uspsocdowloader/help
systemctl reload nginx
```

### Проблема: SSL не получается
**Решение**:
```bash
# Проверьте DNS
nslookup socdownloader.tools.uspeshnyy.ru

# Попробуйте снова
certbot --nginx -d socdownloader.tools.uspeshnyy.ru --force-renewal
```

### Проблема: Telegram Mini App не открывается
**Решение**:
```bash
# Проверьте CORS заголовки
curl -I https://socdownloader.tools.uspeshnyy.ru | grep -i "access-control"

# Должно быть: access-control-allow-origin: *
```

## 📞 Контакты

Если что-то не работает:
- Telegram: [@smit_support](https://t.me/smit_support)
- GitHub Issues: https://github.com/ircitdev/UspSocDownloader/issues

---

**Deployment date**: 02.03.2026
**Commit**: 4f78d68
**Domain**: socdownloader.tools.uspeshnyy.ru
