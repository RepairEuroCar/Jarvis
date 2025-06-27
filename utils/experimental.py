import asyncio
import logging
from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Dict


experimental_usage: Dict[str, int] = defaultdict(int)


def experimental_feature(risk: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator marking a function as experimental.

    When the wrapped function runs a warning is logged and the usage count is
    incremented in ``experimental_usage``.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        name = func.__name__
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                logging.warning(
                    f"⚠ Experimental feature {name} activated (risk={risk})"
                )
                experimental_usage[name] += 1
                return await func(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logging.warning(
                f"⚠ Experimental feature {name} activated (risk={risk})"
            )
            experimental_usage[name] += 1
            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = ["experimental_feature", "experimental_usage"]
