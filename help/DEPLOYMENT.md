# 🚀 Deployment Instructions - Web Documentation

## Настройка поддомена socdownloader.tools.uspeshnyy.ru

### 1. SSH на сервер

```bash
ssh root@31.44.7.144
```

### 2. Перейти в директорию проекта

```bash
cd /opt/uspsocdowloader
```

### 3. Создать директорию для веб-документации (если не существует)

```bash
mkdir -p help
```

### 4. Скопировать index.html

Из локальной машины:

```bash
scp help/index.html root@31.44.7.144:/opt/uspsocdowloader/help/
```

Или на сервере (pull from GitHub):

```bash
cd /opt/uspsocdowloader
git pull origin master
```

### 5. Установить certbot (если не установлен)

```bash
apt update
apt install certbot python3-certbot-nginx -y
```

### 6. Создать Nginx конфигурацию

```bash
nano /etc/nginx/sites-available/socdownloader-docs
```

Вставить содержимое из `help/nginx.conf` (см. файл в репозитории)

### 7. Включить сайт

```bash
ln -s /etc/nginx/sites-available/socdownloader-docs /etc/nginx/sites-enabled/
```

### 8. Проверить конфигурацию Nginx

```bash
nginx -t
```

Должно вывести: `syntax is ok` и `test is successful`

### 9. Получить SSL сертификат (Let's Encrypt)

```bash
certbot --nginx -d socdownloader.tools.uspeshnyy.ru
```

Следуйте инструкциям certbot:
1. Введите email для уведомлений
2. Согласитесь с Terms of Service (Y)
3. Выберите: Redirect HTTP to HTTPS (2)

### 10. Перезапустить Nginx

```bash
systemctl reload nginx
```

### 11. Проверить статус

```bash
systemctl status nginx
```

### 12. Проверить работу сайта

Откройте в браузере:
```
https://socdownloader.tools.uspeshnyy.ru
```

### 13. Проверить логи (если есть проблемы)

```bash
# Nginx error log
tail -f /var/log/nginx/socdownloader-docs-error.log

# Nginx access log
tail -f /var/log/nginx/socdownloader-docs-access.log
```

---

## Обновление HTML файла

Когда нужно обновить содержимое:

### Вариант 1: Через Git (рекомендуется)

```bash
cd /opt/uspsocdowloader
git pull origin master
# HTML файл автоматически обновится
```

### Вариант 2: Прямая замена

Из локальной машины:

```bash
scp help/index.html root@31.44.7.144:/opt/uspsocdowloader/help/
```

Nginx автоматически подхватит изменения (кэш 1 час).

---

## Проверка DNS

Убедитесь, что А-запись настроена:

```bash
nslookup socdownloader.tools.uspeshnyy.ru
```

Должен вернуть IP: `31.44.7.144`

Если нет - добавьте в DNS панели:

```
Type: A
Name: socdownloader.tools
Value: 31.44.7.144
TTL: 3600
```

---

## Автоматическое обновление SSL сертификата

Certbot автоматически настраивает cron для обновления сертификата.

Проверить:

```bash
systemctl status certbot.timer
```

Если не активен:

```bash
systemctl enable certbot.timer
systemctl start certbot.timer
```

---

## Тестирование в Telegram

После деплоя:

1. Откройте бота: [@UspSocDownloader_bot](https://t.me/UspSocDownloader_bot)
2. Отправьте команду: `/howto`
3. Нажмите кнопку "📖 Открыть руководство"
4. Должен открыться Telegram Mini App с документацией

---

## Безопасность

### Файрвол

Убедитесь, что порты 80 и 443 открыты:

```bash
ufw status
```

Если порты закрыты:

```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw reload
```

### Permissions

Установите правильные права на файлы:

```bash
chown -R www-data:www-data /opt/uspsocdowloader/help
chmod -R 755 /opt/uspsocdowloader/help
```

---

## Мониторинг

### Проверка работы сайта

```bash
curl -I https://socdownloader.tools.uspeshnyy.ru
```

Должен вернуть `200 OK`

### Проверка размера файла

```bash
ls -lh /opt/uspsocdowloader/help/index.html
```

### Проверка обновления

```bash
stat /opt/uspsocdowloader/help/index.html
```

Покажет дату последнего изменения.

---

## Troubleshooting

### Проблема: 502 Bad Gateway

**Причина:** Nginx запущен, но не может найти файл

**Решение:**
```bash
ls -la /opt/uspsocdowloader/help/
# Проверьте наличие index.html

# Проверьте права
chmod 755 /opt/uspsocdowloader/help
chmod 644 /opt/uspsocdowloader/help/index.html
```

### Проблема: 404 Not Found

**Причина:** Неверный путь в конфигурации Nginx

**Решение:**
```bash
# Проверьте root в конфигурации
grep "root" /etc/nginx/sites-available/socdownloader-docs

# Должно быть:
# root /opt/uspsocdowloader/help;
```

### Проблема: SSL certificate not found

**Причина:** Certbot не смог получить сертификат

**Решение:**
```bash
# Проверьте DNS
nslookup socdownloader.tools.uspeshnyy.ru

# Попробуйте получить сертификат снова
certbot --nginx -d socdownloader.tools.uspeshnyy.ru --force-renewal
```

### Проблема: Telegram Mini App не открывается

**Причина:** CORS или HTTPS проблемы

**Решение:**
```bash
# Проверьте заголовки
curl -I https://socdownloader.tools.uspeshnyy.ru | grep -i "access-control"

# Должно быть:
# access-control-allow-origin: *

# Перезагрузите Nginx
systemctl reload nginx
```

---

## Производительность

### Включить HTTP/2

Уже включено в конфигурации:
```nginx
listen 443 ssl http2;
```

### Включить Brotli (опционально)

```bash
apt install libnginx-mod-http-brotli -y

# Добавить в конфигурацию Nginx:
# brotli on;
# brotli_types text/plain text/css text/xml text/javascript application/javascript application/json;
```

### Мониторинг запросов

```bash
# Показать последние 100 запросов
tail -n 100 /var/log/nginx/socdownloader-docs-access.log

# Показать количество запросов
wc -l /var/log/nginx/socdownloader-docs-access.log
```

---

## Backup

Сохраните конфигурацию Nginx:

```bash
cp /etc/nginx/sites-available/socdownloader-docs /root/backups/nginx-socdownloader-docs-$(date +%Y%m%d).conf
```

---

**Deployment completed!** ✅

Сайт доступен: https://socdownloader.tools.uspeshnyy.ru
