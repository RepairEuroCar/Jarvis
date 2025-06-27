import inspect
from typing import Any, Callable, Dict


class FallbackManager:
    """Simple manager for callables with fallback handlers."""

    def __init__(self) -> None:
        self._fallbacks: Dict[Callable[..., Any], Callable[..., Any]] = {}

    def register(self, primary: Callable[..., Any], fallback: Callable[..., Any]) -> None:
        """Register *fallback* for *primary* callable."""
        self._fallbacks[primary] = fallback

    async def execute(
        self,
        primary: Callable[..., Any],
        *args: Any,
        fallback: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute *primary* and fall back on exception."""
        fb = fallback or self._fallbacks.get(primary)
        try:
            result = primary(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception:
            if fb is None:
                raise
            result = fb(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result


default_fallback_manager = FallbackManager()

__all__ = ["FallbackManager", "default_fallback_manager"]
