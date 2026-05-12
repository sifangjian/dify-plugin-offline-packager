from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI

from app.core.lifespan import lifespan


class TestLifespanStartup:
    async def test_creates_httpx_client_on_startup(self):
        app = FastAPI(lifespan=lifespan)
        async with lifespan(app):
            assert hasattr(app.state, "httpx_client")
            assert isinstance(app.state.httpx_client, httpx.AsyncClient)

    async def test_httpx_client_timeout_is_30_seconds(self):
        app = FastAPI(lifespan=lifespan)
        async with lifespan(app):
            client = app.state.httpx_client
            assert client.timeout.read == 30.0
            assert client.timeout.connect == 30.0


class TestLifespanShutdown:
    async def test_calls_aclose_on_shutdown(self):
        app = FastAPI(lifespan=lifespan)
        with patch.object(httpx.AsyncClient, "aclose", new_callable=AsyncMock) as mock_aclose:
            async with lifespan(app):
                pass
            mock_aclose.assert_awaited_once()

    async def test_client_not_accessible_after_shutdown(self):
        app = FastAPI(lifespan=lifespan)
        async with lifespan(app):
            client = app.state.httpx_client
            assert isinstance(client, httpx.AsyncClient)
