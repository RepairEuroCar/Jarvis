import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple


class EventQueue:
    """Asynchronous event queue with priority support."""

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._listeners: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        self._worker: Optional[asyncio.Task] = None
        self._running: bool = False

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

    async def emit(self, event_name: str, *args: Any, priority: int = 0, **kwargs: Any) -> None:
        """Queue an event for processing."""
        await self._queue.put((priority, ("event", (event_name, args, kwargs))))

    async def add_task(self, coro: Coroutine[Any, Any, Any], priority: int = 0) -> None:
        """Queue an arbitrary coroutine to run in background."""
        await self._queue.put((priority, ("task", coro)))

    def subscribe(self, event_name: str, listener: Callable[..., Any]) -> None:
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
