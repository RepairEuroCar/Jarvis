import asyncio
import pytest

from jarvis.secure_event_queue import SecureEventQueue

@pytest.mark.asyncio
async def test_secure_event_queue_happy_path():
    q = SecureEventQueue()
    q.register_channel("c", "t")
    received = []
    q.subscribe("c", "t", lambda v: received.append(v))
    await q.start()
    await q.emit("c", "t", 1)
    await asyncio.sleep(0.05)
    await q.stop()
    assert received == [1]


@pytest.mark.asyncio
async def test_secure_event_queue_invalid_token():
    q = SecureEventQueue()
    q.register_channel("c", "t")
    await q.start()
    with pytest.raises(ValueError):
        await q.emit("c", "bad", 1)
    await q.stop()
