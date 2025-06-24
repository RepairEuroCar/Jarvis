import asyncio
import logging
import time
import tracemalloc
from functools import wraps
from typing import Any, Callable, Dict

from core.metrics import broadcast_metrics

logger = logging.getLogger(__name__)


class ModuleProfiler:
    """Collect execution and memory usage stats for module methods."""

    def __init__(self) -> None:
        self.stats: Dict[str, Dict[str, Dict[str, float | int]]] = {}

    def profile(self, module_name: str, func_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Return a decorator profiling *func*."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    tracemalloc.start()
                    start_time = time.perf_counter()
                    result = await func(*args, **kwargs)
                    elapsed = time.perf_counter() - start_time
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    self._record(module_name, func_name, elapsed, peak)
                    return result

                return async_wrapper

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracemalloc.start()
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                self._record(module_name, func_name, elapsed, peak)
                return result

            return sync_wrapper

        return decorator

    def _record(self, module: str, func: str, elapsed: float, peak: int) -> None:
        self.stats.setdefault(module, {})[func] = {
            "time_sec": round(elapsed, 4),
            "peak_mem_kb": peak // 1024,
        }
        broadcast_metrics({
            "module": module,
            "function": func,
            "time_sec": elapsed,
            "peak_mem_kb": peak // 1024,
            "timestamp": time.time(),
        })
        if elapsed > 1.0 or peak > 10 * 1024 * 1024:
            logger.warning(
                "[Profiler] %s.%s took %.2fs, peak %d KB",
                module,
                func,
                elapsed,
                peak // 1024,
            )

    def get_stats(self) -> Dict[str, Dict[str, Dict[str, float | int]]]:
        """Return collected stats."""
        return self.stats
