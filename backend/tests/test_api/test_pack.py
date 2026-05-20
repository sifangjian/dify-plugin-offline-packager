from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.pack import router as pack_router
from app.models.plugin import Architecture, PackSessionInfo, PackTaskInfo, TaskStatus
from app.services.packager import PackagerService


@pytest.fixture
def app():
    _app = FastAPI()
    _app.include_router(pack_router)
    return _app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestPackEndpoint:
    def test_single_plugin_returns_200(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        now = datetime(2025, 1, 1)
        mock_packager.submit_session.return_value = PackSessionInfo(
            session_id="s-1",
            task_ids=["t-1"],
            created_at=now,
        )
        mock_packager.get_task.return_value = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="langgenius",
            name="agent",
            version="0.0.9",
            source="marketplace",
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        app.state.packager_service = mock_packager

        response = client.post(
            "/api/v1/plugins/pack", json={"plugins": [{"author": "langgenius", "name": "agent", "version": "0.0.9"}]}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "tasks" in data
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "t-1"
        assert data["tasks"][0]["author"] == "langgenius"
        assert data["tasks"][0]["status"] == "pending"

    def test_multiple_plugins_returns_multiple_tasks(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        now = datetime(2025, 1, 1)
        mock_packager.submit_session.return_value = PackSessionInfo(
            session_id="s-1",
            task_ids=["t-1", "t-2"],
            created_at=now,
        )
        mock_packager.get_task.side_effect = [
            PackTaskInfo(
                task_id="t-1",
                session_id="s-1",
                author="a",
                name="n1",
                version="0.1",
                source="marketplace",
                status=TaskStatus.PENDING,
                created_at=now,
                updated_at=now,
            ),
            PackTaskInfo(
                task_id="t-2",
                session_id="s-1",
                author="b",
                name="n2",
                version="0.2",
                source="marketplace",
                status=TaskStatus.PENDING,
                created_at=now,
                updated_at=now,
            ),
        ]
        app.state.packager_service = mock_packager

        response = client.post(
            "/api/v1/plugins/pack",
            json={
                "plugins": [
                    {"author": "a", "name": "n1", "version": "0.1"},
                    {"author": "b", "name": "n2", "version": "0.2"},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2

    def test_empty_plugins_returns_422(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        app.state.packager_service = mock_packager

        response = client.post("/api/v1/plugins/pack", json={"plugins": []})
        assert response.status_code == 422

    def test_architecture_parameter_accepted(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        now = datetime(2025, 1, 1)
        mock_packager.submit_session.return_value = PackSessionInfo(
            session_id="s-1",
            task_ids=["t-1"],
            created_at=now,
        )
        mock_packager.get_task.return_value = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="langgenius",
            name="agent",
            version="0.0.9",
            source="marketplace",
            architecture=Architecture.LINUX_ARM64,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        app.state.packager_service = mock_packager

        response = client.post(
            "/api/v1/plugins/pack",
            json={
                "plugins": [
                    {
                        "author": "langgenius",
                        "name": "agent",
                        "version": "0.0.9",
                        "architecture": "linux-arm64",
                    }
                ]
            },
        )

        assert response.status_code == 200

    def test_architecture_defaults_to_linux_amd64(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        now = datetime(2025, 1, 1)
        mock_packager.submit_session.return_value = PackSessionInfo(
            session_id="s-1",
            task_ids=["t-1"],
            created_at=now,
        )
        mock_packager.get_task.return_value = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="langgenius",
            name="agent",
            version="0.0.9",
            source="marketplace",
            architecture=Architecture.LINUX_AMD64,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        app.state.packager_service = mock_packager

        response = client.post(
            "/api/v1/plugins/pack",
            json={"plugins": [{"author": "langgenius", "name": "agent", "version": "0.0.9"}]},
        )

        assert response.status_code == 200

    def test_invalid_architecture_returns_422(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        app.state.packager_service = mock_packager

        response = client.post(
            "/api/v1/plugins/pack",
            json={
                "plugins": [
                    {
                        "author": "langgenius",
                        "name": "agent",
                        "version": "0.0.9",
                        "architecture": "windows-x86",
                    }
                ]
            },
        )

        assert response.status_code == 422
