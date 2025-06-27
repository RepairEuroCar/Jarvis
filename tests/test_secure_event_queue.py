import asyncio

import pytest

from jarvis.secure_event_queue import SecureEventQueue


@pytest.mark.asyncio
async def test_secure_event_queue_token_validation():
    eq = SecureEventQueue()
    eq.register_token("secret", "tok")
    received = []
    eq.subscribe("secret", lambda x: received.append(x))
    await eq.start()
    await eq.emit("secret", 1, token="tok")
    await eq.emit("secret", 2, token="bad")
    await asyncio.sleep(0.05)
    await eq.stop()
    assert received == [1]


@pytest.mark.asyncio
async def test_secure_event_queue_fallback_to_eventqueue():
    eq = SecureEventQueue()
    await eq.start()
    received = []
    eq.subscribe("no_token", lambda x: received.append(x))
    await eq.emit("no_token", 3)
    await asyncio.sleep(0.05)
    await eq.stop()
    assert received == [3]
