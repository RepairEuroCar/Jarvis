import threading
import time
import asyncio
from typing import Any
import logging

logger = logging.getLogger(__name__)

from core.events import emit_event
from core.metrics import broadcast_metrics
from core.module_registry import get_active_modules
from core.flags import default_flag_manager


class SelfDiagnostics:
    def __init__(self, interval: int = 60, backoff_base: float = 1.0, backoff_max: float = 60.0) -> None:
        self.interval = interval
        self.running = False
        self._thread: threading.Thread | None = None
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self._retries: dict[str, dict[str, float]] = {}

    async def health_check(self) -> bool:
        """Ensure diagnostics thread can access module list."""
        try:
            _ = get_active_modules()
            return True
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("SelfDiagnostics health check failed: %s", exc)
            return False

    def start(self) -> None:
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self.running = False
        if self._thread:
            self._thread.join(timeout=0)

    def _run(self) -> None:
        while self.running:
            modules = get_active_modules()
            for module in modules:
                key = getattr(module, "name", str(id(module)))
                healthy = True
                try:
                    healthy = asyncio.run(module.health_check())
                except Exception:
                    healthy = False

                if not healthy:
                    self._attempt_reconnect(module, key)
                else:
                    self._retries.pop(key, None)

                try:
                    stats = module.get_health_metrics()
                    broadcast_metrics(
                        {
                            "module": getattr(module, "name", str(module)),
                            **stats,
                            "timestamp": time.time(),
                        }
                    )
                    if stats.get("response_time", 0) > stats.get(
                        "threshold", float("inf")
                    ):
                        emit_event(
                            "ModuleDegradationDetected",
                            {
                                "module": getattr(module, "name", str(module)),
                                "details": stats,
                            },
                        )
                        default_flag_manager.flag(
                            getattr(module, "name", str(module)),
                            "Response time threshold exceeded",
                        )
                except Exception as e:  # pragma: no cover - best effort logging
                    emit_event(
                        "ModuleDiagnosticsError",
                        {
                            "module": getattr(module, "name", str(module)),
                            "error": str(e),
                        },
                    )
                    default_flag_manager.flag(
                        getattr(module, "name", str(module)),
                        f"Diagnostics error: {e}",
                    )
            time.sleep(self.interval)

    def _attempt_reconnect(self, module: Any, key: str) -> None:
        info = self._retries.get(key, {"attempts": 0, "next": 0.0})
        if time.time() >= info["next"]:
            if hasattr(module, "reconnect"):
                try:
                    asyncio.run(module.reconnect())
                except Exception:
                    pass
            info["attempts"] += 1
            delay = min(self.backoff_base * (2 ** (info["attempts"] - 1)), self.backoff_max)
            info["next"] = time.time() + delay
        self._retries[key] = info
