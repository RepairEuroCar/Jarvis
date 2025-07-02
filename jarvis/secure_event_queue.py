from typing import Any

from jarvis.event_queue import EventQueue


class SecureEventQueue(EventQueue):
    """EventQueue that validates tokens for registered events."""

    def __init__(self) -> None:
        super().__init__()
        self._tokens: dict[str, str] = {}

    def register_token(self, event_name: str, token: str) -> None:
        """Register *token* for *event_name*."""
        self._tokens[event_name] = token

    def get_token(self, event_name: str) -> None | [str]:
        return self._tokens.get(event_name)

    async def emit(
        self,
        event_name: str,
        *args: Any,
        priority: int = 0,
        token : None | [str] = None,
        **kwargs: Any,
    ) -> None:
        expected = self._tokens.get(event_name)
        if expected is not None and token != expected:
            return
        await super().emit(event_name, *args, priority=priority, **kwargs)
