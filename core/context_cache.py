import time
import threading
from typing import Any, Dict, Tuple


class ContextCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, max_size: int = 1000) -> None:
        self.store: Dict[str, Tuple[Any, float]] = {}
        self.lock = threading.Lock()
        self.max_size = max_size

    def set(self, key: str, value: Any, ttl: float = 60) -> None:
        """Store *value* under *key* for *ttl* seconds."""
        with self.lock:
            if len(self.store) >= self.max_size:
                self._evict()
            self.store[key] = (value, time.time() + ttl)

    def get(self, key: str) -> Any | None:
        """Return cached value for *key* if not expired."""
        with self.lock:
            item = self.store.get(key)
            if not item:
                return None
            value, expire_at = item
            if time.time() > expire_at:
                del self.store[key]
                return None
            return value

    def _evict(self) -> None:
        """Remove the oldest cached item."""
        if self.store:
            self.store.pop(next(iter(self.store)))

    def clear(self) -> None:
        """Clear all cached entries."""
        with self.lock:
            self.store.clear()


context_cache = ContextCache()

__all__ = ["ContextCache", "context_cache"]
