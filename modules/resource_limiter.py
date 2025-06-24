import threading
import time

import psutil

from core.events import emit_event
from core.metrics import broadcast_metrics
from core.module_registry import get_active_modules


class ResourceLimiter:
    def __init__(self, interval: int = 10) -> None:
        self.interval = interval
        self.running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self.running:
            for module in get_active_modules():
                pid = getattr(module, "get_pid", lambda: None)()
                if pid is None:
                    continue
                try:
                    p = psutil.Process(pid)
                    mem_mb = p.memory_info().rss / (1024 * 1024)
                    cpu = p.cpu_percent(interval=0.1)

                    broadcast_metrics(
                        {
                            "module": getattr(module, "name", str(module)),
                            "memory": mem_mb,
                            "cpu": cpu,
                            "timestamp": time.time(),
                        }
                    )

                    quota = getattr(
                        module,
                        "get_resource_quota",
                        lambda: {"memory": float("inf"), "cpu": float("inf")},
                    )()
                    if mem_mb > quota.get("memory", float("inf")) or cpu > quota.get(
                        "cpu", float("inf")
                    ):
                        emit_event(
                            "ResourceLimitWarning",
                            {
                                "module": getattr(module, "name", str(module)),
                                "memory": mem_mb,
                                "cpu": cpu,
                                "quota": quota,
                            },
                        )
                except Exception as e:
                    emit_event(
                        "ResourceMonitorError",
                        {
                            "module": getattr(module, "name", str(module)),
                            "error": str(e),
                        },
                    )
            time.sleep(self.interval)

    def stop(self) -> None:
        self.running = False
        if self._thread:
            self._thread.join(timeout=0)
