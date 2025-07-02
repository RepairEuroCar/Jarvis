import asyncio
import logging

import pytest

from jarvis.core.main import Jarvis


class DummyVoiceInterface:
    def __init__(self, jarvis):
        self.jarvis = jarvis
        self.started = False

    def start(self):
        self.started = True


@pytest.mark.asyncio
async def test_initialize_logs(monkeypatch, caplog):
    monkeypatch.setattr("voice.interface.VoiceInterface", DummyVoiceInterface)
    jarvis = Jarvis()

    async def dummy_start():
        pass

    jarvis.event_queue.start = dummy_start
    jarvis.sensor_manager.start = dummy_start
    jarvis.event_queue.subscribe = lambda *a, **kw: None

    caplog.set_level(logging.INFO)
    await jarvis.initialize()

    msgs = [r.getMessage() for r in caplog.records]
    assert any("Initializing voice_interface" in m for m in msgs)
    assert any("Initializing event_queue" in m for m in msgs)
    assert any("Initializing sensor_manager" in m for m in msgs)


@pytest.mark.asyncio
async def test_initialize_warns_on_slow_step(monkeypatch, caplog):
    monkeypatch.setattr("voice.interface.VoiceInterface", DummyVoiceInterface)
    jarvis = Jarvis()

    async def slow_start():
        await asyncio.sleep(0.01)

    jarvis.sensor_manager.start = slow_start

    async def event_start():
        await asyncio.sleep(0)

    jarvis.event_queue.start = event_start
    jarvis.event_queue.subscribe = lambda *a, **kw: None

    monkeypatch.setitem(Jarvis.INIT_THRESHOLDS, "sensor_manager", 0.0)
    caplog.set_level(logging.WARNING)

    await jarvis.initialize()

    assert any(
        "sensor_manager initialization took" in r.getMessage() for r in caplog.records
    )
