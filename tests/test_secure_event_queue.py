import asyncio
from unittest.mock import Mock

import pytest

from jarvis.secure_event_queue import SecureEventQueue


@pytest.mark.asyncio
async def test_invalid_token_logs_warning():
    logger = Mock()
    eq = SecureEventQueue(valid_tokens={"good"}, logger=logger)
    await eq.start()

    received = []

    def listener(value):
        received.append(value)

    eq.subscribe("test", listener)

    await eq.emit("bad", "test", 42)
    await asyncio.sleep(0.05)
    await eq.stop()

    assert not received
    logger.warning.assert_called()
    assert "Invalid token" in logger.warning.call_args[0][0]
