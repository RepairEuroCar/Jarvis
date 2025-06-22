import asyncio
from typing import Any, List

from jarvis.event_queue import EventQueue


class SensorManager:
    """Manage asynchronous sensors and publish events."""

    def __init__(self, jarvis: Any, event_queue: EventQueue) -> None:
        self.jarvis = jarvis
        self.event_queue = event_queue
        self._tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start all configured sensors."""
        if self.jarvis.settings.voice_enabled and self.jarvis.voice_interface:
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
        """Periodic tick for future scheduled tasks."""
        while True:
            try:
                await asyncio.sleep(60)
                await self.event_queue.emit("scheduled_tick")
            except asyncio.CancelledError:
                break
