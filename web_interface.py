from __future__ import annotations

"""Simple FastAPI web interface for Jarvis project generation."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone, timedelta
import time

from utils.logger import get_logger

from modules.task_splitter import task_split
from plugins.project_generator import _generate_files


BASE_DIR = Path(__file__).parent
GENERATED_DIR = BASE_DIR / "generated_projects"
GENERATED_DIR.mkdir(exist_ok=True)

logger = get_logger().getChild("WebInterface")
START_TIME = datetime.now(timezone.utc)

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start_ts = time.time()
    start_iso = datetime.now(timezone.utc).isoformat()
    logger.info("Start request %s %s at %s", request.method, request.url.path, start_iso)
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render upload form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    """Handle text file upload and generate project."""
    if not file.filename:
        return templates.TemplateResponse(
            "index.html", {"request": request, "error": "No file provided."}
        )

    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / file.filename
        tmp_path.write_bytes(await file.read())

        tasks = await task_split(str(tmp_path))

        out_dir = GENERATED_DIR / tmp_path.stem
        out_dir.mkdir(exist_ok=True)

        spec_text = tmp_path.read_text(encoding="utf-8")
        files = _generate_files(spec_text, str(out_dir))

        zip_path = shutil.make_archive(str(out_dir), "zip", str(out_dir))
        zip_name = Path(zip_path).name

    context = {
        "request": request,
        "tasks": tasks,
        "files": [Path(p).name for p in files],
        "zip_name": zip_name,
    }
    return templates.TemplateResponse("result.html", context)


@app.get("/download/{zip_name}")
async def download(zip_name: str) -> FileResponse:
    """Return generated project archive."""
    path = GENERATED_DIR / zip_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/zip", filename=zip_name)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_interface:app", host="0.0.0.0", port=8000)
