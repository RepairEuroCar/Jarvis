import threading
import time

from core.events import emit_event
from core.metrics import broadcast_metrics
from core.module_registry import get_active_modules
from core.flags import default_flag_manager


class SelfDiagnostics:
    def __init__(self, interval: int = 60) -> None:
        self.interval = interval
        self.running = False
        self._thread: threading.Thread | None = None

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
