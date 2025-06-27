import asyncio

import pytest

from jarvis.event_queue import EventQueue


@pytest.mark.asyncio
async def test_event_queue_listener_called():
    eq = EventQueue()
    await eq.start()
    received = []

    def listener(value):
        received.append(value)

    eq.subscribe("test", listener)
    await eq.emit("test", 42)
    # allow queue to process
    await asyncio.sleep(0.05)
    await eq.stop()

    assert received == [42]


@pytest.mark.asyncio
async def test_event_queue_background_task():
    eq = EventQueue()
    await eq.start()
    flag = False

    async def work():
        nonlocal flag
        flag = True

    await eq.add_task(work())
    await asyncio.sleep(0.05)
    await eq.stop()

    assert flag


@pytest.mark.asyncio
async def test_event_queue_stop():
    eq = EventQueue()
    await eq.start()
    await eq.stop()
    assert eq._running is False
    assert eq._worker is None


@pytest.mark.asyncio
async def test_event_queue_secure_channel():
    eq = EventQueue({"secret": "tok"})
    await eq.start()

    received = []

    def listener(value):
        received.append(value)

    # correct token
    eq.subscribe("secret", listener, token="tok")
    await eq.emit("secret", 5, token="tok")
    await asyncio.sleep(0.05)
    assert received == [5]

    with pytest.raises(ValueError):
        eq.subscribe("secret", listener, token="bad")
    with pytest.raises(ValueError):
        await eq.emit("secret", 6, token="bad")

    await eq.stop()
