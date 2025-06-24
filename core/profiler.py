import asyncio
import logging
import time
import tracemalloc
from typing import Any, Callable


class ModuleProfiler:
    """Simple profiler for Jarvis modules."""

    def __init__(self) -> None:
        self.stats: dict[str, dict[str, Any]] = {}

    def profile(
        self, module_name: str, func_name: str
    ) -> Callable[[Callable], Callable]:
        """Decorator to profile a module method."""

        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):

                async def async_wrapper(*args, **kwargs):
                    tracemalloc.start()
                    start_time = time.perf_counter()
                    result = await func(*args, **kwargs)
                    elapsed = time.perf_counter() - start_time
                    _current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    self._record(module_name, func_name, elapsed, peak)
                    return result

                return async_wrapper

            def sync_wrapper(*args, **kwargs):
                tracemalloc.start()
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                _current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                self._record(module_name, func_name, elapsed, peak)
                return result

            return sync_wrapper

        return decorator

    def _record(self, module: str, func: str, elapsed: float, peak: int) -> None:
        self.stats.setdefault(module, {})[func] = {
            "time_seconds": round(elapsed, 4),
            "peak_memory_kb": peak // 1024,
        }
        if elapsed > 1.0 or peak > 10 * 1024 * 1024:
            logging.warning(
                f"[Profiler] {module}.{func} took {elapsed:.2f}s, "
                f"peak memory {peak // 1024} KB"
            )

    def get_stats(self) -> dict[str, dict[str, Any]]:
        return self.stats


default_profiler = ModuleProfiler()
