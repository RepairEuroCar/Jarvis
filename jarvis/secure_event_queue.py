import asyncio
import logging
from typing import Any, Callable, Iterable, Set

from .event_queue import EventQueue
from utils.logger import get_logger


class SecureEventQueue(EventQueue):
    """Event queue that requires a valid token to emit events."""

    def __init__(self, valid_tokens: Iterable[str] | None = None, logger: logging.Logger | None = None) -> None:
        super().__init__()
        self._tokens: Set[str] = set(valid_tokens or [])
        self._logger = logger or get_logger()

    def register_token(self, token: str) -> None:
        """Allow ``token`` to emit events."""
        self._tokens.add(token)

    def revoke_token(self, token: str) -> None:
        """Remove ``token`` from allowed list."""
        self._tokens.discard(token)

    def subscribe(self, event_name: str, listener: Callable[..., Any]) -> None:  # type: ignore[override]
        self._logger.debug("Subscribing listener %r to event '%s'", listener, event_name)
        super().subscribe(event_name, listener)

    async def emit(self, token: str, event_name: str, *args: Any, priority: int = 0, **kwargs: Any) -> None:
        """Emit an event only if ``token`` is valid."""
        if token not in self._tokens:
            self._logger.warning("Invalid token for event '%s'", event_name)
            return
        self._logger.debug("Emitting event '%s' with token '%s'", event_name, token)
        await super().emit(event_name, *args, priority=priority, **kwargs)

    async def _run(self) -> None:  # type: ignore[override]
        while True:
            priority, item = await self._queue.get()
            if item[0] == "__stop__":
                break
            if item[0] == "event":
                event_name, args, kwargs = item[1]
                for listener in list(self._listeners.get(event_name, [])):
                    try:
                        if asyncio.iscoroutinefunction(listener):
                            await listener(*args, **kwargs)
                        else:
                            listener(*args, **kwargs)
                    except Exception as exc:
                        self._logger.exception(
                            "Listener %r failed for event '%s': %s", listener, event_name, exc
                        )
            elif item[0] == "task":
                coro = item[1]
                try:
                    await coro
                except Exception as exc:
                    self._logger.exception("Background task failed: %s", exc)
            self._queue.task_done()
