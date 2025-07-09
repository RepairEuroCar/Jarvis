import logging
import time
from collections import defaultdict

from core.events import emit_event


class FlagManager:
    """Track module anomalies and flag problematic modules."""

    def __init__(self, error_threshold: int = 3, window: float = 60.0) -> None:
        self.error_threshold = error_threshold
        self.window = window
        self.flags: dict[str, str] = {}
        self._errors: dict[str, list[float]] = defaultdict(list)

    def flag(self, module_name: str, reason: str) -> None:
        """Mark *module_name* as flagged for *reason*."""
        self.flags[module_name] = reason
        logging.warning(
            f"[\u26a0\ufe0f FLAGGED] \u041c\u043e\u0434\u0443\u043b\u044c {module_name} \u043f\u043e\u043c\u0435\u0447\u0435\u043d \u0444\u043b\u0430\u0433\u043e\u043c: {reason}"
        )
        emit_event("ModuleAnomalyFlagged", {"module": module_name, "reason": reason})

    def is_flagged(self, module_name: str) -> bool:
        return module_name in self.flags

    def clear_flag(self, module_name: str) -> None:
        self.flags.pop(module_name, None)

    def record_error(self, module_name: str, error: Exception) -> None:
        """Record an exception for *module_name* and flag if threshold exceeded."""
        now = time.time()
        history = self._errors[module_name]
        history[:] = [t for t in history if now - t < self.window]
        history.append(now)
        if len(history) >= self.error_threshold:
            self.flag(module_name, f"Error threshold exceeded: {error}")
            history.clear()


# Global manager used by built-in modules
default_flag_manager = FlagManager()

__all__ = ["FlagManager", "default_flag_manager"]
