import asyncio
from collections.abc import Iterable
from typing import Any, Callable


class FallbackManager:
    """Manage optional fallbacks for callable execution."""

    def __init__(self) -> None:
        self._fallbacks: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        """Register *func* as fallback under *name*."""
        self._fallbacks[name] = func

    async def execute(
        self,
        primary: Callable[..., Any],
        *args: Any,
        fallback_name: str | None = None,
        exceptions: Iterable[type[Exception]] | type[Exception] = Exception,
        **kwargs: Any,
    ) -> Any:
        """Execute *primary*, optionally using a registered fallback.

        Parameters
        ----------
        primary:
            Function or coroutine to execute.
        fallback_name:
            Name of a previously registered fallback to call if *primary*
            raises one of *exceptions*.
        exceptions:
            Exception or iterable of exceptions that trigger the fallback.
        """

        try:
            if asyncio.iscoroutinefunction(primary):
                return await primary(*args, **kwargs)
            return primary(*args, **kwargs)
        except exceptions:
            if not fallback_name:
                raise
            fallback = self._fallbacks.get(fallback_name)
            if fallback is None:
                raise
            if asyncio.iscoroutinefunction(fallback):
                return await fallback(*args, **kwargs)
            return fallback(*args, **kwargs)


default_fallback_manager = FallbackManager()

__all__ = ["FallbackManager", "default_fallback_manager"]
