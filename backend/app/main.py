from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.lifespan import lifespan

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

app = FastAPI(
    title="Dify Plugin Offline Packager",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_router)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

_settings = get_settings()
_static_dir = Path(_settings.STATIC_DIR)
if not _static_dir.is_absolute():
    _static_dir = _PROJECT_ROOT / _static_dir

if _static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="static-assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str) -> FileResponse:
        file_path = _static_dir / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_static_dir / "index.html")
