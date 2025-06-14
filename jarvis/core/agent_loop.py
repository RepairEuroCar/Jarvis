import asyncio
import logging
from typing import Any, Dict

from jarvis.event_queue import EventQueue

logger = logging.getLogger("Jarvis.AgentLoop")


class AgentLoop:
    """Simple async event loop for Jarvis.

    The loop waits for events from :class:`EventQueue`, processes user
    messages with ``Jarvis.nlu`` and routes them to ``Brain.think``.
    Results of the reasoning are emitted back on the queue as
    ``"action_result"`` events.
    """

    def __init__(self, jarvis: Any) -> None:
        self.jarvis = jarvis
        self.queue = EventQueue()
        self._running = False
        self._runner: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.queue.subscribe("user_input", self._on_user_input)
        await self.queue.start()
        self._runner = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        await self.queue.stop()
        if self._runner:
            self._runner.cancel()
            try:
                await self._runner
            except asyncio.CancelledError:
                pass
            self._runner = None

    async def _run(self) -> None:
        while self._running:
            await asyncio.sleep(0.1)

    async def _on_user_input(self, user_id: int, text: str, **kwargs: Any) -> None:
        """Handle ``user_input`` events."""
        try:
            parsed = await self.jarvis.nlu.process(text)
            if parsed.get("intent") == "exit":
                await self.stop()
                return
            context: Dict[str, Any] = {"user_id": user_id, **kwargs}
            context.update(parsed)
            result = await self.jarvis.brain.think(text, context)
            await self.queue.emit("action_result", result)
        except Exception as e:  # pragma: no cover - logging only
            logger.exception("Failed to process input: %s", e)

    async def run(self) -> None:
        """Start the loop and run until stopped."""
        await self.start()
        if self._runner:
            await self._runner

