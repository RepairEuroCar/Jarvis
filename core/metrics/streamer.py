import asyncio
import json
import threading
from typing import Any, Set

import websockets
from websockets.server import WebSocketServerProtocol

connected_clients: Set[WebSocketServerProtocol] = set()
_loop: asyncio.AbstractEventLoop | None = None


async def _metrics_handler(websocket: WebSocketServerProtocol) -> None:
    connected_clients.add(websocket)
    try:
        async for _ in websocket:
            await websocket.send("ACK")
    finally:
        connected_clients.discard(websocket)


async def _serve_forever(host: str, port: int) -> None:
    async with websockets.serve(_metrics_handler, host, port):
        await asyncio.Event().wait()


def run_server(host: str = "localhost", port: int = 8765) -> None:
    """Start the websocket metrics server in a background thread."""
    global _loop
    if _loop and _loop.is_running():
        return
    _loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=_loop.run_until_complete,
        args=(_serve_forever(host, port),),
        daemon=True,
    )
    thread.start()


def broadcast_metrics(data: dict[str, Any]) -> None:
    """Send a metrics update to all connected clients."""
    if _loop is None or not connected_clients:
        return
    msg = json.dumps(data)

    async def _broadcast() -> None:
        await asyncio.gather(
            *[ws.send(msg) for ws in connected_clients], return_exceptions=True
        )

    asyncio.run_coroutine_threadsafe(_broadcast(), _loop)
