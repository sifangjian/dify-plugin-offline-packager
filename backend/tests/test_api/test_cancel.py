from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.pack import router as pack_router
from app.core.exceptions import AppException, app_exception_handler
from app.services.packager import PackagerService


@pytest.fixture
def app():
    _app = FastAPI()
    _app.include_router(pack_router)
    _app.add_exception_handler(AppException, app_exception_handler)
    return _app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestCancelEndpoint:
    def test_cancel_session_returns_200(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.cancel_session.return_value = True
        app.state.packager_service = mock_packager

        response = client.post("/api/v1/plugins/cancel/s-1")

        assert response.status_code == 200
        mock_packager.cancel_session.assert_awaited_once_with("s-1")

    def test_cancel_nonexistent_session_returns_404(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.cancel_session.return_value = False
        app.state.packager_service = mock_packager

        response = client.post("/api/v1/plugins/cancel/nonexistent")

        assert response.status_code == 404
