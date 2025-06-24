import asyncio
import json

import pytest
import websockets

from core.metrics import broadcast_metrics, run_server


@pytest.mark.asyncio
async def test_metrics_streamer_broadcast():
    port = 8765
    run_server(port=port)
    await asyncio.sleep(0.1)
    async with websockets.connect(f"ws://localhost:{port}") as ws:
        await ws.send("hello")
        ack = await ws.recv()
        assert ack == "ACK"
        broadcast_metrics({"foo": "bar"})
        data = json.loads(await ws.recv())
        assert data["foo"] == "bar"
