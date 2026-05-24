from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.pack import router as pack_router
from app.core.exceptions import AppException, app_exception_handler
from app.models.plugin import PackTaskInfo, PluginSource, TaskStatus
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


def _make_task(task_id="t-1", status=TaskStatus.SUCCESS, result_file_path=None, **kwargs):
    now = datetime(2025, 1, 1)
    defaults = dict(
        task_id=task_id,
        session_id="s-1",
        author="langgenius",
        name="agent",
        version="0.0.9",
        source=PluginSource.MARKETPLACE,
        status=status,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    task = PackTaskInfo(**defaults)
    if result_file_path:
        task.result_file_path = result_file_path
    return task


class TestDownloadEndpoint:
    def test_successful_download_returns_200(self, client, app, tmp_path):
        result_file = tmp_path / "agent-0.0.9-offline.difypkg"
        result_file.write_bytes(b"fake-difypkg-content")

        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.get_task.return_value = _make_task(result_file_path=result_file)
        mock_packager._storage = AsyncMock()
        app.state.packager_service = mock_packager

        response = client.get("/api/v1/plugins/download/t-1")
        assert response.status_code == 200
        assert "agent-0.0.9-linux-amd64-offline.difypkg" in response.headers.get("content-disposition", "")

    def test_nonexistent_task_returns_404(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.get_task.return_value = None
        app.state.packager_service = mock_packager

        response = client.get("/api/v1/plugins/download/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"
        assert "未找到该打包任务" in data["error"]["message"]

    def test_non_success_task_returns_400(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.get_task.return_value = _make_task(status=TaskStatus.FAILED)
        app.state.packager_service = mock_packager

        response = client.get("/api/v1/plugins/download/t-1")
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "TASK_NOT_READY"

    def test_pending_task_returns_400(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.get_task.return_value = _make_task(status=TaskStatus.PENDING)
        app.state.packager_service = mock_packager

        response = client.get("/api/v1/plugins/download/t-1")
        assert response.status_code == 400

    def test_missing_result_file_returns_404(self, client, app, tmp_path):
        nonexistent = tmp_path / "nonexistent.difypkg"

        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.get_task.return_value = _make_task(result_file_path=nonexistent)
        app.state.packager_service = mock_packager

        response = client.get("/api/v1/plugins/download/t-1")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "FILE_NOT_FOUND"

    def test_filename_format(self, client, app, tmp_path):
        result_file = tmp_path / "agent-0.0.9-offline.difypkg"
        result_file.write_bytes(b"content")

        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.get_task.return_value = _make_task(result_file_path=result_file)
        app.state.packager_service = mock_packager

        response = client.get("/api/v1/plugins/download/t-1")
        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        assert "agent-0.0.9-linux-amd64-offline.difypkg" in content_disposition
