import asyncio
from typing import Callable, Awaitable, Dict

from utils.logger import get_logger
from core.events import emit_event


class FallbackManager:
    """Manage fallback handlers for Jarvis modules."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[[Exception], Awaitable[None]]] = {}
        self._logger = get_logger().getChild("FallbackManager")

    def register_fallback(
        self, module_name: str, handler: Callable[[Exception], Awaitable[None]]
    ) -> None:
        """Register an async *handler* for *module_name*."""
        self._handlers[module_name] = handler
        self._logger.debug("Registered fallback for %s", module_name)

    async def activate(self, module_name: str, exc: Exception) -> None:
        """Execute fallback handler for *module_name* if available."""
        handler = self._handlers.get(module_name)
        if not handler:
            self._logger.warning("No fallback registered for %s", module_name)
            return
        try:
            await handler(exc)
            self._logger.info("Activated fallback for %s", module_name)
            emit_event("FallbackActivated", {"module": module_name, "error": str(exc)})
        except Exception as e:  # pragma: no cover - best effort logging
            self._logger.exception("Fallback for %s failed", module_name, exc_info=e)


__all__ = ["FallbackManager"]
