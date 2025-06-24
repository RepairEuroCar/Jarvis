import psutil
import time
import threading
from datetime import datetime


class SystemHealthMonitor:
    """Background monitor for system health metrics."""

    def __init__(self, interval: float = 30.0) -> None:
        self.interval = interval
        self.running = False
        self.thread = threading.Thread(target=self._monitor, daemon=True)

    def start(self) -> None:
        self.running = True
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread.is_alive():
            self.thread.join()

    def _monitor(self) -> None:
        while self.running:
            self._check_health()
            time.sleep(self.interval)

    def _check_health(self) -> None:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        disk = psutil.disk_usage("/")
        alerts = []

        if cpu > 90:
            alerts.append(f"⚠️ High CPU: {cpu}%")
        if mem.percent > 85:
            alerts.append(f"⚠️ High RAM: {mem.percent}% used")
        if disk.percent > 90:
            alerts.append(f"⚠️ Low disk space: {disk.percent}% used")

        if alerts:
            message = "\n".join(alerts)
            print(f"[{datetime.now()}] SYSTEM HEALTH ALERT:\n{message}")


_monitor_instance: SystemHealthMonitor | None = None


def register(jarvis) -> None:
    """Register the system health monitor plugin."""

    global _monitor_instance
    if _monitor_instance is not None:
        return

    monitor = SystemHealthMonitor()
    _monitor_instance = monitor
    monitor.start()

    def _on_shutdown() -> None:
        monitor.stop()

    jarvis.subscribe_event("jarvis_shutdown", _on_shutdown)
