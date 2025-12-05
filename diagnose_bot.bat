@echo off
REM Скрипт для подключения к серверу и диагностики бота
REM Требует: plink.exe (PuTTY) или sshpass

setlocal enabledelayedexpansion

set SERVER=31.44.7.144
set USER=root
set PASSWORD=4x6EltSOS41MbhyD

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║  ДИАГНОСТИКА TELEGRAM БОТА НА СЕРВЕРЕ                     ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Проверка наличия plink
where plink.exe >nul 2>&1
if errorlevel 1 (
    echo ❌ plink.exe не найден
    echo.
    echo Установите PuTTY с https://www.putty.org/
    echo или используйте WSL (Windows Subsystem for Linux)
    exit /b 1
)

echo Подключаюсь к серверу %SERVER%...
echo.

REM Команда для проверки статуса
plink.exe -pw %PASSWORD% %USER%@%SERVER% ^
    "systemctl status uspsocdowloader --no-pager; " ^
    "echo ; " ^
    "echo === Последние 30 логов === ; " ^
    "journalctl -u uspsocdowloader -n 30 --no-pager"

if errorlevel 1 (
    echo.
    echo ❌ Ошибка подключения
    exit /b 1
)

echo.
echo ✅ Диагностика завершена
