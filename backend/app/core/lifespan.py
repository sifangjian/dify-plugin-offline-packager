from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from httpx import AsyncClient

from app.core.config import get_settings
from app.services.packager import PackagerService
from app.services.storage import StorageService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    httpx_client = AsyncClient(timeout=30.0)
    app.state.httpx_client = httpx_client

    storage = StorageService(work_dir=Path(settings.WORK_DIR))
    packager = PackagerService(
        httpx_client=httpx_client,
        settings=settings,
        storage=storage,
    )
    app.state.packager_service = packager
    app.state.storage_service = storage

    packager.start()

    yield

    await packager.stop()
    await httpx_client.aclose()
