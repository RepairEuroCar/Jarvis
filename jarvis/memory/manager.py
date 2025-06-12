import os
import json
import time
import shutil
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("Jarvis.Memory")

class MemoryManager:
    def __init__(self, memory_file: str = "jarvis_memory.json"):
        self.memory_file = memory_file
        self.memory = self._initialize_memory()

    def _initialize_memory(self) -> Dict[str, Any]:
        """Инициализация структуры памяти"""
        base_structure = {
            "user_info": {"name": "User"},
            "system": {},
            "voice_settings": {},
            "commands_history": []
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

    def remember(self, key: str, value: Any, category: str = "general") -> bool:
        """Сохранение данных в память"""
        try:
            keys = key.split('.')
            current = self.memory
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = {
                "value": value,
                "timestamp": time.time(),
                "category": category
            }
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            return False

    def query(self, key: str) -> Optional[Any]:
        """Получение данных по ключу"""
        try:
            parts = key.split('.')
            current = self.memory
            for part in parts:
                if isinstance(current, dict):
                    if part.startswith('[') and part.endswith(']'):
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
            parts = key.split('.')
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
                return True
            return False
        except Exception:
            return False

    def recall(self, key: str) -> Optional[Any]:
        """Извлечение данных из памяти"""
        try:
            keys = key.split('.')
            current = self.memory
            for k in keys:
                current = current[k]
            return current.get("value") if isinstance(current, dict) else current
        except KeyError:
            return None
