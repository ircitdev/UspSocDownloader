"""
Модуль перевода текста и OCR через OpenAI API
"""
import os
import re
import base64
from pathlib import Path
from typing import List, Tuple
from openai import AsyncOpenAI
from src.utils.logger import get_logger

logger = get_logger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


def is_russian_text(text: str) -> bool:
    """Проверяет, является ли текст преимущественно русским"""
    if not text:
        return True

    # Убираем эмодзи, ссылки и спецсимволы
    clean_text = re.sub(r'https?://\S+', '', text)
    clean_text = re.sub(r'[^\w\s]', '', clean_text)
    clean_text = clean_text.strip()

    if not clean_text:
        return True

    # Считаем кириллические символы
    cyrillic_count = len(re.findall(r'[а-яёА-ЯЁ]', clean_text))
    latin_count = len(re.findall(r'[a-zA-Z]', clean_text))

    total = cyrillic_count + latin_count
    if total == 0:
        return True

    # Если больше 30% кириллицы - считаем русским
    return cyrillic_count / total > 0.3


async def translate_to_russian(text: str) -> str:
    """Переводит текст на русский через OpenAI"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Ты переводчик. Переведи текст на русский язык. ВАЖНО: Сохрани ВСЕ HTML-теги (<pre>, </pre>, <b>, </b> и др.) без изменений! Сохрани форматирование, эмодзи и ссылки. Отвечай только переводом, без пояснений."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=0.3,
            max_tokens=4000
        )

        translated = response.choices[0].message.content
        logger.info(f"Translated {len(text)} chars to Russian")
        return translated

    except Exception as e:
        logger.error(f"Translation error: {e}")
        return f"Ошибка перевода: {str(e)[:100]}"


REWRITE_STYLES = {
    "expert": "Перепиши текст в экспертном стиле: используй профессиональную лексику, факты, авторитетный тон. Сохрани основной смысл.",
    "humor": "Перепиши текст в юмористическом стиле: добавь шутки, иронию, лёгкий тон. Сохрани основной смысл.",
    "friendly": "Перепиши текст в дружелюбном стиле: тёплый тон, простые слова, как будто пишешь другу. Сохрани основной смысл."
}


async def rewrite_text(text: str, style: str) -> str:
    """Делает рерайт текста в указанном стиле через OpenAI"""
    try:
        style_prompt = REWRITE_STYLES.get(style, REWRITE_STYLES["friendly"])

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"{style_prompt} ВАЖНО: Сохрани ВСЕ HTML-теги (<pre>, </pre>, <b>, </b> и др.) без изменений! Отвечай только рерайтом, без пояснений. Пиши на русском языке."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=0.7,
            max_tokens=4000
        )

        rewritten = response.choices[0].message.content
        logger.info(f"Rewritten {len(text)} chars in {style} style")
        return rewritten

    except Exception as e:
        logger.error(f"Rewrite error: {e}")
        return f"Ошибка рерайта: {str(e)[:100]}"


def encode_image_to_base64(image_path: str) -> str:
    """Кодирует изображение в base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def check_image_has_text(image_path: str) -> bool:
    """Проверяет, содержит ли изображение текст (быстрая проверка)"""
    try:
        base64_image = encode_image_to_base64(image_path)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Does this image contain readable text (words, sentences, paragraphs)? Answer only YES or NO."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            max_tokens=10
        )

        answer = response.choices[0].message.content.strip().upper()
        has_text = "YES" in answer
        logger.info(f"Image {image_path} has text: {has_text}")
        return has_text

    except Exception as e:
        logger.error(f"Error checking image for text: {e}")
        return False


async def check_images_have_text(image_paths: List[str]) -> bool:
    """Проверяет, содержат ли изображения текст (проверяет первое)"""
    if not image_paths:
        return False
    # Проверяем только первое изображение для экономии
    return await check_image_has_text(image_paths[0])


OCR_SYSTEM_PROMPT = """Ты OCR система для извлечения полезного контента с изображений.

ВАЖНО - Извлекай ТОЛЬКО основной контент изображения:
- Заголовки, абзацы, списки, формулы, определения
- Полезную информацию, факты, инструкции

НЕ ИЗВЛЕКАЙ служебную информацию:
- Имена аккаунтов, никнеймы (@username)
- Названия каналов/профилей
- Водяные знаки, логотипы
- Призывы к подписке/лайкам ("подпишись", "follow", "comment")
- Рекламные фразы ("GET ACCESS NOW", "FREE", "скидка")
- Служебные надписи интерфейса

Сохрани структуру и форматирование текста.
Если полезного текста нет - ответь пустой строкой.
Отвечай только извлечённым текстом."""


async def extract_text_from_images(image_paths: List[str]) -> str:
    """Извлекает текст со всех изображений через GPT-4 Vision"""
    try:
        all_texts = []

        for i, image_path in enumerate(image_paths):
            if not Path(image_path).exists():
                continue

            base64_image = encode_image_to_base64(image_path)

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": OCR_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Извлеки полезный контент с этого изображения:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000
            )

            text = response.choices[0].message.content.strip()
            if text:
                # Убираем markdown-форматирование, которое GPT иногда добавляет
                # Удаляем блоки ```plaintext ... ``` и просто ``` ... ```
                text = re.sub(r'^```(?:plaintext|text|markdown)?\s*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
                text = text.strip()

                if not text:
                    continue

                # Форматируем с номером слайда и блоком <pre> для копирования (HTML)
                slide_num = i + 1
                # Экранируем HTML-спецсимволы
                escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                formatted = f"📄 Слайд {slide_num}:\n<pre>{escaped_text}</pre>"
                all_texts.append(formatted)
                logger.info(f"Extracted {len(text)} chars from image {slide_num}")

        combined_text = "\n\n".join(all_texts)
        return combined_text if combined_text else "Полезный текст на изображениях не найден."

    except Exception as e:
        logger.error(f"OCR error: {e}")
        return f"Ошибка распознавания текста: {str(e)[:100]}"
