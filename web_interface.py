from __future__ import annotations

"""Simple FastAPI web interface for Jarvis project generation."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from modules.task_splitter import task_split
from plugins.project_generator import _generate_files


BASE_DIR = Path(__file__).parent
GENERATED_DIR = BASE_DIR / "generated_projects"
GENERATED_DIR.mkdir(exist_ok=True)

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_interface:app", host="0.0.0.0", port=8000)
