import asyncio

import pytest

from jarvis.secure_event_queue import SecureEventQueue


TOKEN = "secret"
WRONG = "wrong"


@pytest.mark.asyncio
async def test_secure_event_queue_authorized():
    eq = SecureEventQueue(TOKEN)
    await eq.start()
    received = []

    def listener(value):
        received.append(value)

    eq.subscribe("test", listener, token=TOKEN)
    await eq.emit("test", 42, token=TOKEN)
    await asyncio.sleep(0.05)
    await eq.stop()

    assert received == [42]


@pytest.mark.asyncio
async def test_secure_event_queue_wrong_token():
    eq = SecureEventQueue(TOKEN)
    await eq.start()

    with pytest.raises(PermissionError):
        eq.subscribe("test", lambda x: x, token=WRONG)

    with pytest.raises(PermissionError):
        await eq.emit("test", 1, token=WRONG)

    await eq.stop()


@pytest.mark.asyncio
async def test_secure_event_queue_no_unauthorized_events():
    eq = SecureEventQueue(TOKEN)
    await eq.start()
    received = []

    with pytest.raises(PermissionError):
        eq.subscribe("test", lambda x: received.append(x), token=WRONG)

    eq.subscribe("test", lambda x: received.append(x), token=TOKEN)

    with pytest.raises(PermissionError):
        await eq.emit("test", 99, token=WRONG)

    await eq.emit("test", 99, token=TOKEN)
    await asyncio.sleep(0.05)
    await eq.stop()

    assert received == [99]
