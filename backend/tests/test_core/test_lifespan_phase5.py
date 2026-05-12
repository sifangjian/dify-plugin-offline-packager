from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.lifespan import lifespan
from app.services.packager import PackagerService
from app.services.storage import StorageService


class TestLifespanPackagerService:
    async def test_creates_packager_service_on_startup(self):
        app = FastAPI(lifespan=lifespan)
        async with lifespan(app):
            assert hasattr(app.state, "packager_service")
            assert isinstance(app.state.packager_service, PackagerService)

    async def test_creates_storage_service_on_startup(self):
        app = FastAPI(lifespan=lifespan)
        async with lifespan(app):
            assert hasattr(app.state, "storage_service")
            assert isinstance(app.state.storage_service, StorageService)

    async def test_packager_consumer_task_is_running(self):
        app = FastAPI(lifespan=lifespan)
        async with lifespan(app):
            packager = app.state.packager_service
            assert packager._consumer_task is not None
            assert not packager._consumer_task.done()

    async def test_httpx_client_timeout_is_30_seconds(self):
        app = FastAPI(lifespan=lifespan)
        async with lifespan(app):
            client = app.state.httpx_client
            assert client.timeout.read == 30.0
            assert client.timeout.connect == 30.0


class TestLifespanShutdown:
    async def test_stops_packager_on_shutdown(self):
        app = FastAPI(lifespan=lifespan)
        with patch.object(PackagerService, "stop", new_callable=AsyncMock) as mock_stop:
            async with lifespan(app):
                pass
            mock_stop.assert_awaited_once()

    async def test_closes_httpx_client_on_shutdown(self):
        app = FastAPI(lifespan=lifespan)
        with patch.object(httpx.AsyncClient, "aclose", new_callable=AsyncMock) as mock_aclose:
            async with lifespan(app):
                pass
            mock_aclose.assert_awaited_once()


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        app = FastAPI(lifespan=lifespan)

        @app.get("/api/v1/health")
        async def health_check():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
