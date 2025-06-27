import asyncio
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Coroutine, Dict


module_stats: Dict[str, Dict[str, Any]] = defaultdict(
    lambda: {"calls": 0, "errors": 0, "avg_duration": 0.0}
)


def track_usage(module_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator tracking calls, duration and errors for a module."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start
                    stat = module_stats[module_name]
                    stat["calls"] += 1
                    stat["avg_duration"] = (
                        (stat["avg_duration"] * (stat["calls"] - 1)) + duration
                    ) / stat["calls"]
                    return result
                except Exception:
                    module_stats[module_name]["errors"] += 1
                    raise

            return async_wrapper
        else:

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start
                    stat = module_stats[module_name]
                    stat["calls"] += 1
                    stat["avg_duration"] = (
                        (stat["avg_duration"] * (stat["calls"] - 1)) + duration
                    ) / stat["calls"]
                    return result
                except Exception:
                    module_stats[module_name]["errors"] += 1
                    raise

            return wrapper

    return decorator


def get_module_stats() -> Dict[str, Dict[str, Any]]:
    """Return collected module usage statistics."""
    return dict(module_stats)
