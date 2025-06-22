import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from jarvis.core.sensor_manager import SensorManager, ScheduledTask


class DummyJarvis:
    def __init__(self, voice=None):
        self.settings = SimpleNamespace(voice_enabled=True)
        self.voice_interface = voice


@pytest.mark.asyncio
async def test_microphone_loop_emits(monkeypatch):
    events = []
    event_queue = SimpleNamespace(emit=AsyncMock(side_effect=lambda name, *args, **kw: events.append((name, args, kw))))
    voice = SimpleNamespace(listen=AsyncMock(side_effect=["hello", asyncio.CancelledError()]))
    jarvis = DummyJarvis(voice)
    sm = SensorManager(jarvis, event_queue)

    # speed up sleep inside the loop
    original_sleep = asyncio.sleep

    async def fast_sleep(_):
        await original_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    await sm._microphone_loop()

    assert ("voice_command", ("hello",), {}) in events


@pytest.mark.asyncio
async def test_scheduled_loop_emits_tick(monkeypatch):
    events = []
    event_queue = SimpleNamespace(emit=AsyncMock(side_effect=lambda name, **kw: events.append((name, kw))))
    jarvis = DummyJarvis(None)
    sm = SensorManager(jarvis, event_queue)

    async def dummy_cb(j):
        pass

    sm.register_scheduled_task(dummy_cb, interval=1)
    task = sm.scheduled_tasks[0]
    task.next_run = 0  # force immediate run

    original_sleep = asyncio.sleep

    async def fast_sleep(_):
        await original_sleep(0)
    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    loop_task = asyncio.create_task(sm._scheduled_loop())
    await original_sleep(0.01)
    loop_task.cancel()
    await asyncio.gather(loop_task, return_exceptions=True)

    assert events and events[0][0] == "scheduled_tick"
    assert events[0][1]["task"] is task
