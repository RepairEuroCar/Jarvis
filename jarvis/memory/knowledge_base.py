import json
import os
from typing import Any


class KnowledgeBase:
    """Persistent storage for facts and experience."""

    def __init__(self, kb_file: str = "knowledge.json") -> None:
        self.kb_file = kb_file
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if os.path.exists(self.kb_file):
            try:
                with open(self.kb_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        try:
            with open(self.kb_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_fact(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def get_fact(self, key: str) -> Any:
        return self.data.get(key)

    def update_fact(self, key: str, value: Any) -> bool:
        if key in self.data:
            self.data[key] = value
            self.save()
            return True
        return False

    def delete_fact(self, key: str) -> bool:
        if key in self.data:
            del self.data[key]
            self.save()
            return True
        return False

    def list_facts(self) -> dict[str, Any]:
        return dict(self.data)
