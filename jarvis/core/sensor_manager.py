import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, List

from jarvis.event_queue import EventQueue


@dataclass
class ScheduledTask:
    callback: Callable[[Any], Awaitable[Any]]
    interval: float
    next_run: float = field(default_factory=lambda: time.monotonic())


class SensorManager:
    """Manage asynchronous sensors and publish events."""

    def __init__(self, jarvis: Any, event_queue: EventQueue) -> None:
        self.jarvis = jarvis
        self.event_queue = event_queue
        self._tasks: List[asyncio.Task] = []
        self.scheduled_tasks: List[ScheduledTask] = []

    def register_scheduled_task(
        self, callback: Callable[[Any], Awaitable[Any]], interval: float
    ) -> None:
        """Register a new scheduled task."""
        self.scheduled_tasks.append(
            ScheduledTask(callback=callback, interval=interval, next_run=time.monotonic() + interval)
        )

    async def start(self) -> None:
        """Start all configured sensors."""
        if (
            self.jarvis.settings.voice_enabled
            and self.jarvis.voice_interface
            and self.jarvis.voice_interface.microphone
        ):
            self._tasks.append(asyncio.create_task(self._microphone_loop()))
        # Scheduled tasks run always for now
        self._tasks.append(asyncio.create_task(self._scheduled_loop()))

    async def stop(self) -> None:
        """Stop all running sensor tasks."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _microphone_loop(self) -> None:
        """Continuously listen on the microphone and emit events."""
        voice = self.jarvis.voice_interface
        if not voice:
            return
        while True:
            try:
                text = await voice.listen()
                if text:
                    await self.event_queue.emit("voice_command", text)
            except asyncio.CancelledError:
                break
            await asyncio.sleep(0.1)

    async def _scheduled_loop(self) -> None:
        """Emit scheduled tick events for registered tasks."""
        while True:
            try:
                now = time.monotonic()
                for task in list(self.scheduled_tasks):
                    if now >= task.next_run:
                        await self.event_queue.emit("scheduled_tick", task=task)
                        task.next_run = now + task.interval
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
