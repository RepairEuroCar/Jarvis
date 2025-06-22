import json
<<<<<<< HEAD
import logging
=======
>>>>>>> main
import os
import shutil
import time
from typing import Any, Dict, Optional

from utils.logger import get_logger

logger = get_logger().getChild("Memory")



class MemoryManager:
    def __init__(
        self, memory_file: str = "jarvis_memory.json", auto_save: bool = False
    ):
        """Initialize the memory manager.

        Parameters
        ----------
        memory_file: str
            Path to the JSON file used for persistence.
        auto_save: bool
            If True any modification will trigger :meth:`save` automatically.
        """
        self.memory_file = memory_file
        self.auto_save = auto_save
        self.memory = self._initialize_memory()

    def _initialize_memory(self) -> Dict[str, Any]:
        """Инициализация структуры памяти"""
        base_structure = {
            "user_info": {"name": "User"},
            "system": {},
            "voice_settings": {},
            "commands_history": [],
        }

        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    return {**base_structure, **loaded}
            except Exception as e:
                logger.error(f"Ошибка загрузки памяти: {e}")

        return base_structure

    def save(self):
        """Сохранение памяти в файл"""
        try:
            if os.path.exists(self.memory_file):
                shutil.copy(self.memory_file, f"{self.memory_file}.bak")

            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения памяти: {e}")

    def remember(
        self, key: str, value: Any, category: str = "general"
    ) -> bool:
        """Сохранение данных в память"""
        try:
            keys = key.split(".")
            current = self.memory
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = {
                "value": value,
                "timestamp": time.time(),
                "category": category,
            }
            if self.auto_save:
                self.save()
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            return False

    def query(self, key: str) -> Optional[Any]:
        """Получение данных по ключу"""
        try:
            parts = key.split(".")
            current = self.memory
            for part in parts:
                if isinstance(current, dict):
                    if part.startswith("[") and part.endswith("]"):
                        current = current[int(part[1:-1])]
                    else:
                        current = current.get(part)
                else:
                    return None
                if current is None:
                    return None
            return current
        except Exception:
            return None

    def forget(self, key: str) -> bool:
        """Удаление записи из памяти"""
        try:
            parts = key.split(".")
            current = self.memory
            parent = None
            last_part = None
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return False
                parent = current
                last_part = part
                current = current[part]
            if parent and last_part in parent:
                del parent[last_part]
                if self.auto_save:
                    self.save()
                return True
            return False
        except Exception:
            return False

    def recall(self, key: str) -> Optional[Any]:
        """Извлечение данных из памяти"""
        try:
            keys = key.split(".")
            current = self.memory
            for k in keys:
                current = current[k]
            return (
                current.get("value") if isinstance(current, dict) else current
            )
        except KeyError:
            return None

    def search(self, query: str) -> Dict[str, Any]:
        """Поиск значений по подстроке ключа."""

        results: Dict[str, Any] = {}

        def _search(obj: Any, path: str) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_path = f"{path}.{k}" if path else k
                    if query in k:
                        results[new_path] = v
                    _search(v, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _search(item, f"{path}[{i}]")

        _search(self.memory, "")
        return results
