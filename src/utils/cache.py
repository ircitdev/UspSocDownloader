"""
Файловый кэш для сохранения данных между перезапусками бота
"""
import json
import os
from pathlib import Path
from typing import Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

CACHE_DIR = Path("/opt/uspsocdowloader/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class FileCache:
    """Простой файловый кэш на основе JSON"""
    
    def __init__(self, name: str, max_items: int = 1000):
        self.name = name
        self.max_items = max_items
        self.file_path = CACHE_DIR / f"{name}.json"
        self._data = self._load()
    
    def _load(self) -> dict:
        """Загружает кэш из файла"""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data)} items from cache {self.name}")
                    return data
            except Exception as e:
                logger.error(f"Error loading cache {self.name}: {e}")
        return {}
    
    def _save(self):
        """Сохраняет кэш в файл"""
        try:
            # Ограничиваем размер кэша
            if len(self._data) > self.max_items:
                # Удаляем старые записи (первые по порядку добавления)
                keys = list(self._data.keys())
                for key in keys[:len(keys) - self.max_items]:
                    del self._data[key]
            
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving cache {self.name}: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Получает значение из кэша"""
        return self._data.get(str(key))
    
    def set(self, key: str, value: Any):
        """Устанавливает значение в кэш"""
        self._data[str(key)] = value
        self._save()
    
    def delete(self, key: str):
        """Удаляет значение из кэша"""
        if str(key) in self._data:
            del self._data[str(key)]
            self._save()
    
    def __contains__(self, key: str) -> bool:
        return str(key) in self._data
    
    def __getitem__(self, key: str) -> Any:
        return self._data[str(key)]
    
    def __setitem__(self, key: str, value: Any):
        self.set(key, value)


# Создаем кэши
image_paths_cache = FileCache("image_paths", max_items=500)
original_texts_cache = FileCache("original_texts", max_items=500)
