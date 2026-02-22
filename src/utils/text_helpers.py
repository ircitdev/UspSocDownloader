"""
Вспомогательные функции для работы с текстом
"""
import html


def safe_format_error(error: Exception, max_length: int = 100) -> str:
    """
    Безопасно форматирует текст ошибки для отправки в Telegram.
    Экранирует HTML-символы, чтобы избежать ошибок парсинга.

    Args:
        error: Исключение для форматирования
        max_length: Максимальная длина текста ошибки

    Returns:
        Экранированный текст ошибки
    """
    error_text = str(error)[:max_length]
    return html.escape(error_text)
