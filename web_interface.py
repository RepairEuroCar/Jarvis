from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import | None

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_interface")

# Конфигурация
BASE_DIR = Path(__file__).parent
GENERATED_DIR = BASE_DIR / "generated_projects"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

GENERATED_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)


# Модели данных
class UploadResponse(BaseModel):
    success: bool
    message : None | [str] = None
    download_url : None | [str] = None
    files : None | [list[str]] = None


# Инициализация приложения
app = FastAPI(
    title="File Processing API",
    description="API для загрузки и обработки файлов",
    version="1.0.0",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Шаблоны
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Обработчики ошибок
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Error: {exc.detail}")
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )


# Middleware для логирования
@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"completed in {process_time:.2f}ms"
    )
    return response


# Роуты
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница с формой загрузки"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "max_file_size": "10MB", "allowed_types": [".txt"]},
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="Текстовый файл для обработки"),
):
    """
    Обработка загруженного файла

    Поддерживает только .txt файлы до 10MB
    """
    try:
        # Валидация файла
        if not file.filename:
            raise HTTPException(400, "No file provided")

        if not file.filename.lower().endswith(".txt"):
            raise HTTPException(400, "Only .txt files are allowed")

        if file.size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(413, "File too large (max 10MB)")

        # Обработка файла
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / file.filename
            content = await file.read()

            # Сохранение оригинального файла
            tmp_path.write_bytes(content)

            # Создание директории для результатов
            out_dir = GENERATED_DIR / tmp_path.stem
            out_dir.mkdir(exist_ok=True)

            # Здесь должна быть ваша логика обработки файла
            processed_files = process_file(tmp_path, out_dir)

            # Создание архива
            zip_path = shutil.make_archive(str(out_dir), "zip", str(out_dir))
            zip_name = Path(zip_path).name

            return {
                "success": True,
                "download_url": f"/download/{zip_name}",
                "files": processed_files,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File processing failed: {e}", exc_info=True)
        raise HTTPException(500, "File processing failed") from e


@app.get("/download/{zip_name}")
async def download_file(zip_name: str):
    """Скачивание обработанных файлов"""
    file_path = GENERATED_DIR / zip_name
    if not file_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(file_path, media_type="application/zip", filename=zip_name)


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# Вспомогательные функции
def process_file(input_path: Path, output_dir: Path) -> list[str]:
    """Пример функции обработки файла"""
    # Здесь должна быть ваша логика обработки
    output_file = output_dir / f"processed_{input_path.name}"
    output_file.write_text(f"Processed: {input_path.read_text()}")
    return [str(output_file.relative_to(output_dir))]


def _format_iso_duration(delta: timedelta) -> str:
    """Форматирование длительности"""
    total_seconds = int(delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"P{days}DT{hours}H{minutes}M{seconds}S"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_interface:app", host="0.0.0.0", port=8000, reload=True)
