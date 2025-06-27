import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Optional


class EventQueue:
    """Asynchronous event queue with priority support and optional channel tokens."""

    def __init__(self, channel_tokens: Optional[Dict[str, str]] = None) -> None:
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._listeners: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        self._channel_tokens: Dict[str, str] = channel_tokens or {}
        self._worker: Optional[asyncio.Task] = None
        self._running: bool = False

    def register_channel(self, name: str, token: str) -> None:
        """Register a secured channel with the given token."""
        self._channel_tokens[name] = token

    async def start(self) -> None:
        if not self._running:
            self._running = True
            self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        await self._queue.put((0, ("__stop__", None)))
        if self._worker:
            await self._worker
            self._worker = None

    async def emit(
        self,
        event_name: str,
        *args: Any,
        priority: int = 0,
        token: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Queue an event for processing. Validates token if required."""
        expected = self._channel_tokens.get(event_name)
        if expected is not None and token != expected:
            raise ValueError("Invalid token for channel")
        await self._queue.put((priority, ("event", (event_name, args, kwargs))) )

    async def add_task(
        self, coro: Coroutine[Any, Any, Any], priority: int = 0
    ) -> None:
        """Queue an arbitrary coroutine to run in background."""
        await self._queue.put((priority, ("task", coro)))

    def subscribe(
        self,
        event_name: str,
        listener: Callable[..., Any],
        token: Optional[str] = None,
    ) -> None:
        """Register a listener. Validates token if the channel is secured."""
        expected = self._channel_tokens.get(event_name)
        if expected is not None and token != expected:
            raise ValueError("Invalid token for channel")
        self._listeners[event_name].append(listener)

    async def _run(self) -> None:
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
                    except Exception:
                        pass
            elif item[0] == "task":
                coro = item[1]
                try:
                    await coro
                except Exception:
                    pass
            self._queue.task_done()
