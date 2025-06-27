import threading
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger("jarvis").getChild("ConfigReloader")


class _ReloadHandler(FileSystemEventHandler):
    def __init__(self, reloader: "ConfigReloader") -> None:
        super().__init__()
        self.reloader = reloader

    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path) == self.reloader.path:
            self.reloader.reload()

    def on_created(self, event):
        if not event.is_directory and Path(event.src_path) == self.reloader.path:
            self.reloader.reload()


class ConfigReloader:
    """Watch ``config.yaml`` and hot-reload changed sections."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._callbacks: Dict[str, List[Callable[[dict], None]]] = {}
        self._data: Dict[str, dict] = self._load()
        self._lock = threading.Lock()

        self._observer = Observer()
        handler = _ReloadHandler(self)
        self._observer.schedule(handler, str(self.path.parent), recursive=False)
        try:
            self._observer.start()
        except Exception as e:  # pragma: no cover - watcher may fail
            logger.error(f"Failed to start config observer: {e}")

    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()

    # ------------------------------------------------------------------
    def subscribe(self, section: str, callback: Callable[[dict], None]) -> None:
        """Register a callback invoked when ``section`` changes."""
        self._callbacks.setdefault(section, []).append(callback)

    # ------------------------------------------------------------------
    def _load(self) -> Dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:  # pragma: no cover - corrupted file
            logger.error(f"Failed loading {self.path}: {e}")
            return {}

    # ------------------------------------------------------------------
    def reload(self, sections: Optional[Sequence[str]] = None) -> None:
        """Reload the configuration file and notify callbacks."""
        with self._lock:
            new_data = self._load()
            watch_sections = sections or list(self._callbacks.keys())
            for section in watch_sections:
                if new_data.get(section) != self._data.get(section):
                    self._data[section] = new_data.get(section)
                    for cb in self._callbacks.get(section, []):
                        try:
                            cb(self._data.get(section) or {})
                        except Exception:  # pragma: no cover - callback failure
                            logger.exception("Callback for %s failed", section)
            self._data.update({k: v for k, v in new_data.items() if k not in self._data})
