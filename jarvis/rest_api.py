"""Minimal REST API for issuing commands to Jarvis."""

from fastapi import FastAPI
from pydantic import BaseModel

from jarvis.core.main import Jarvis

app = FastAPI()
jarvis = Jarvis()


class CommandRequest(BaseModel):
    text: str
    voice: bool = False


@app.on_event("startup")
async def startup() -> None:
    await jarvis.initialize()


@app.post("/command")
async def command(req: CommandRequest) -> dict:
    result = await jarvis.handle_command(req.text, is_voice=req.voice)
    return {"result": result}


@app.get("/status")
async def status() -> dict:
    return {"state": jarvis.machine.state}


@app.get("/metrics")
async def metrics() -> dict:
    """Return collected module profiler statistics."""
    return jarvis.module_manager.profiler.get_stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("jarvis.rest_api:app", host="0.0.0.0", port=8001)
