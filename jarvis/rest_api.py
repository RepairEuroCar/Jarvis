"""Minimal REST API for issuing commands to Jarvis."""

import time
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from pydantic import BaseModel

from jarvis.core.main import Jarvis
from utils.logger import get_logger

logger = get_logger().getChild("REST")
START_TIME = datetime.now(timezone.utc)

app = FastAPI()
jarvis = Jarvis()


class CommandRequest(BaseModel):
    text: str
    voice: bool = False


@app.on_event("startup")
async def startup() -> None:
    await jarvis.initialize()


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start_ts = time.time()
    start_iso = datetime.now(timezone.utc).isoformat()
    logger.info(
        "Start request %s %s at %s", request.method, request.url.path, start_iso
    )
    try:
        response = await call_next(request)
        return response
    finally:
        end_iso = datetime.now(timezone.utc).isoformat()
        duration_ms = (time.time() - start_ts) * 1000
        logger.info(
            "End request %s %s at %s duration=%.2fms",
            request.method,
            request.url.path,
            end_iso,
            duration_ms,
        )


@app.post("/command")
async def command(req: CommandRequest) -> dict:
    result = await jarvis.handle_command(req.text, is_voice=req.voice)
    return {"result": result}


@app.get("/status")
async def status() -> dict:
    return {"state": jarvis.machine.state}


def _format_iso_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"P{days}DT{hours}H{minutes}M{seconds}S"


@app.get("/uptime")
async def uptime() -> dict:
    delta = datetime.now(timezone.utc) - START_TIME
    return {"uptime": _format_iso_duration(delta)}


@app.get("/selfcheck")
async def selfcheck() -> dict:
    results = await jarvis.module_manager.health_check_all()
    return {"modules": results}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("jarvis.rest_api:app", host="0.0.0.0", port=8001)
