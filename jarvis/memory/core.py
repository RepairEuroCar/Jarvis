import time
from typing import Any


class MemoryCore:
    """Unified short-term memory for events, dialogues and reasoning."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._dialogues: list[dict[str, Any]] = []
        self._reasoning: list[dict[str, Any]] = []

    # Event APIs
    def add_event(self, name: str, payload: Any) -> int:
        record = {"name": name, "payload": payload, "timestamp": time.time()}
        self._events.append(record)
        return len(self._events) - 1

    def get_event(self, index: int) -> None | [dict[str, Any]]:
        if 0 <= index < len(self._events):
            return self._events[index]
        return None

    def get_events(self, limit : None | [int] = None) -> list[dict[str, Any]]:
        return self._events[-limit:] if limit else list(self._events)

    def update_event(self, index: int, payload: Any) -> bool:
        if 0 <= index < len(self._events):
            self._events[index]["payload"] = payload
            return True
        return False

    def delete_event(self, index: int) -> bool:
        if 0 <= index < len(self._events):
            del self._events[index]
            return True
        return False

    # Dialogue APIs
    def add_dialogue(self, speaker: str, text: str) -> int:
        record = {"speaker": speaker, "text": text, "timestamp": time.time()}
        self._dialogues.append(record)
        return len(self._dialogues) - 1

    def get_dialogue(self, index: int) -> None | [dict[str, Any]]:
        if 0 <= index < len(self._dialogues):
            return self._dialogues[index]
        return None

    def get_dialogues(self, limit : None | [int] = None) -> list[dict[str, Any]]:
        return self._dialogues[-limit:] if limit else list(self._dialogues)

    def update_dialogue(self, index: int, text: str) -> bool:
        if 0 <= index < len(self._dialogues):
            self._dialogues[index]["text"] = text
            return True
        return False

    def delete_dialogue(self, index: int) -> bool:
        if 0 <= index < len(self._dialogues):
            del self._dialogues[index]
            return True
        return False

    # Reasoning APIs
    def add_reasoning(self, problem: str, solution: Any) -> int:
        record = {"problem": problem, "solution": solution, "timestamp": time.time()}
        self._reasoning.append(record)
        return len(self._reasoning) - 1

    def get_reasoning(self, index: int) -> None | [dict[str, Any]]:
        if 0 <= index < len(self._reasoning):
            return self._reasoning[index]
        return None

    def get_reasoning_history(
        self, limit : None | [int] = None
    ) -> list[dict[str, Any]]:
        return self._reasoning[-limit:] if limit else list(self._reasoning)

    def update_reasoning(self, index: int, solution: Any) -> bool:
        if 0 <= index < len(self._reasoning):
            self._reasoning[index]["solution"] = solution
            return True
        return False

    def delete_reasoning(self, index: int) -> bool:
        if 0 <= index < len(self._reasoning):
            del self._reasoning[index]
            return True
        return False
