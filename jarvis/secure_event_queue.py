import asyncio
from typing import Any, Callable, Optional

from .event_queue import EventQueue


class SecureEventQueue(EventQueue):
    """Event queue that requires a token for subscriptions and emissions."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def _validate_token(self, token: str) -> None:
        if token != self._token:
            raise PermissionError("Invalid token")

    def subscribe(
        self, event_name: str, listener: Callable[..., Any], *, token: str
    ) -> None:
        """Register a listener for an event with token verification."""
        self._validate_token(token)
        super().subscribe(event_name, listener)

    async def emit(
        self,
        event_name: str,
        *args: Any,
        token: str,
        priority: int = 0,
        **kwargs: Any,
    ) -> None:
        """Emit an event with token verification."""
        self._validate_token(token)
        await super().emit(event_name, *args, priority=priority, **kwargs)
