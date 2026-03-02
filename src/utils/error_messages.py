"""User-friendly error messages and handling."""
from typing import Dict, Any, Optional

# Словарь понятных сообщений об ошибках
ERROR_MESSAGES: Dict[str, Dict[str, Any]] = {
    "instagram_rate_limit": {
        "emoji": "⏳",
        "title": "Instagram ограничил доступ",
        "message": "Instagram временно ограничил количество запросов",
        "suggestion": "Попробуйте через 5-10 минут",
        "retry_after": 300,  # секунд
        "show_retry_button": True
    },
    "instagram_private": {
        "emoji": "🔒",
        "title": "Пост недоступен",
        "message": "Этот пост приватный или удален",
        "suggestion": "Проверьте, что ссылка правильная и профиль публичный",
        "retry_after": 0,
        "show_retry_button": False
    },
    "instagram_login_required": {
        "emoji": "🔐",
        "title": "Требуется авторизация",
        "message": "Для загрузки этого контента нужна авторизация в Instagram",
        "suggestion": "К сожалению, такой контент недоступен",
        "retry_after": 0,
        "show_retry_button": False
    },
    "youtube_age_restricted": {
        "emoji": "🔞",
        "title": "Возрастные ограничения",
        "message": "Видео с возрастными ограничениями",
        "suggestion": "К сожалению, такие видео недоступны через бота",
        "retry_after": 0,
        "show_retry_button": False
    },
    "youtube_premium_only": {
        "emoji": "💎",
        "title": "Только для Premium",
        "message": "Это видео доступно только для YouTube Premium",
        "suggestion": "Попробуйте другое видео или получите Premium подписку",
        "retry_after": 0,
        "show_retry_button": False
    },
    "file_too_large": {
        "emoji": "📦",
        "title": "Файл слишком большой",
        "message": "Файл превышает лимит Telegram (50 MB для видео)",
        "suggestion": "Попробуйте скачать в более низком качестве через настройки",
        "retry_after": 0,
        "show_retry_button": False
    },
    "timeout": {
        "emoji": "⌛",
        "title": "Превышено время ожидания",
        "message": "Загрузка заняла слишком много времени",
        "suggestion": "Попробуйте позже или выберите меньшее качество",
        "retry_after": 60,
        "show_retry_button": True
    },
    "network_error": {
        "emoji": "🌐",
        "title": "Ошибка сети",
        "message": "Не удалось подключиться к серверу",
        "suggestion": "Проверьте подключение и попробуйте еще раз",
        "retry_after": 30,
        "show_retry_button": True
    },
    "invalid_url": {
        "emoji": "❌",
        "title": "Неверная ссылка",
        "message": "Ссылка не распознана или повреждена",
        "suggestion": "Проверьте правильность ссылки и отправьте снова",
        "retry_after": 0,
        "show_retry_button": False
    },
    "platform_not_supported": {
        "emoji": "🚫",
        "title": "Платформа не поддерживается",
        "message": "Эта платформа пока не поддерживается ботом",
        "suggestion": "Поддерживаются: Instagram, YouTube, TikTok, VK, Twitter",
        "retry_after": 0,
        "show_retry_button": False
    },
    "download_failed": {
        "emoji": "💔",
        "title": "Ошибка загрузки",
        "message": "Не удалось скачать файл",
        "suggestion": "Попробуйте еще раз или выберите другую ссылку",
        "retry_after": 30,
        "show_retry_button": True
    },
    "geo_restricted": {
        "emoji": "🌍",
        "title": "Географические ограничения",
        "message": "Контент недоступен в вашем регионе",
        "suggestion": "К сожалению, этот контент заблокирован для вашей страны",
        "retry_after": 0,
        "show_retry_button": False
    },
    "copyright": {
        "emoji": "©️",
        "title": "Защищено авторским правом",
        "message": "Контент заблокирован из-за авторских прав",
        "suggestion": "Этот контент нельзя скачать из-за правообладателя",
        "retry_after": 0,
        "show_retry_button": False
    },
    "server_error": {
        "emoji": "🔧",
        "title": "Ошибка сервера",
        "message": "Внутренняя ошибка на сервере платформы",
        "suggestion": "Подождите немного и попробуйте снова",
        "retry_after": 120,
        "show_retry_button": True
    },
    "daily_limit_exceeded": {
        "emoji": "📊",
        "title": "Превышен дневной лимит",
        "message": "Вы достигли лимита бесплатных загрузок (10/день)",
        "suggestion": "Подождите до завтра или получите Premium для безлимитных загрузок",
        "retry_after": 0,
        "show_retry_button": False
    }
}


def get_error_type_from_exception(error: Exception) -> str:
    """Определить тип ошибки по исключению.

    Args:
        error: Exception объект

    Returns:
        Тип ошибки (ключ из ERROR_MESSAGES)
    """
    error_str = str(error).lower()

    # Instagram errors
    if "429" in error_str or "too many requests" in error_str:
        return "instagram_rate_limit"
    if "private" in error_str or "not available" in error_str:
        return "instagram_private"
    if "login" in error_str or "authenticate" in error_str:
        return "instagram_login_required"

    # YouTube errors
    if "age" in error_str and "restrict" in error_str:
        return "youtube_age_restricted"
    if "premium" in error_str:
        return "youtube_premium_only"

    # File errors
    if "too large" in error_str or "file size" in error_str:
        return "file_too_large"

    # Network errors
    if "timeout" in error_str:
        return "timeout"
    if "network" in error_str or "connection" in error_str:
        return "network_error"

    # URL errors
    if "invalid" in error_str and "url" in error_str:
        return "invalid_url"

    # Geo restrictions
    if "geo" in error_str or "region" in error_str or "country" in error_str:
        return "geo_restricted"

    # Copyright
    if "copyright" in error_str or "dmca" in error_str:
        return "copyright"

    # Server errors
    if "500" in error_str or "502" in error_str or "503" in error_str:
        return "server_error"

    # Default
    return "download_failed"


def get_user_friendly_error(
    error_type: str,
    include_emoji: bool = True,
    include_suggestion: bool = True
) -> str:
    """Получить понятное сообщение об ошибке.

    Args:
        error_type: Тип ошибки (ключ из ERROR_MESSAGES)
        include_emoji: Включить эмодзи в начало
        include_suggestion: Включить подсказку

    Returns:
        Форматированное сообщение об ошибке
    """
    error = ERROR_MESSAGES.get(error_type)

    if not error:
        return f"❌ Произошла ошибка: {error_type}"

    parts = []

    # Эмодзи и заголовок
    if include_emoji:
        parts.append(f"{error['emoji']} <b>{error['title']}</b>")
    else:
        parts.append(f"<b>{error['title']}</b>")

    parts.append("")

    # Основное сообщение
    parts.append(error['message'])

    # Подсказка
    if include_suggestion and error['suggestion']:
        parts.append("")
        parts.append(f"💡 {error['suggestion']}")

    return "\n".join(parts)


def format_error_with_retry(
    error_type: str,
    original_url: Optional[str] = None
) -> tuple[str, Optional[dict]]:
    """Форматировать ошибку с кнопкой повтора если нужно.

    Args:
        error_type: Тип ошибки
        original_url: Оригинальный URL для повтора

    Returns:
        Tuple (message_text, keyboard_data или None)
    """
    error = ERROR_MESSAGES.get(error_type)

    if not error:
        return (get_user_friendly_error(error_type), None)

    message = get_user_friendly_error(error_type)

    # Добавляем кнопку повтора если нужно
    keyboard_data = None
    if error['show_retry_button'] and original_url:
        keyboard_data = {
            "show_retry": True,
            "url": original_url,
            "retry_after": error['retry_after']
        }

    return (message, keyboard_data)


def detect_error_from_logs(log_message: str) -> Optional[str]:
    """Определить тип ошибки из лог-сообщения.

    Args:
        log_message: Сообщение из логов

    Returns:
        Тип ошибки или None
    """
    log_lower = log_message.lower()

    # Проверяем по ключевым словам
    if "429" in log_message or "rate limit" in log_lower:
        return "instagram_rate_limit"

    if "timeout" in log_lower:
        return "timeout"

    if "connection" in log_lower or "network" in log_lower:
        return "network_error"

    if "500" in log_message or "502" in log_message or "503" in log_message:
        return "server_error"

    return None
