from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.sse import router as sse_router
from app.core.exceptions import AppException, app_exception_handler
from app.models.plugin import PackSessionInfo, PackTaskInfo, PluginSource, TaskStatus
from app.models.sse import SessionCompletedEvent, SSEEventType
from app.services.packager import PackagerService


@pytest.fixture
def app():
    _app = FastAPI()
    _app.include_router(sse_router)
    _app.add_exception_handler(AppException, app_exception_handler)
    return _app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestSSEEndpoint404:
    def test_nonexistent_session_returns_404(self, client, app):
        mock_packager = AsyncMock(spec=PackagerService)
        mock_packager.get_session.return_value = None
        app.state.packager_service = mock_packager

        response = client.get("/sse/pack/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"


class TestSSEEventGenerator:
    async def test_generator_yields_session_started(self):
        from app.api.sse import _event_generator

        mock_packager = AsyncMock(spec=PackagerService)
        now = datetime(2025, 1, 1)
        session = PackSessionInfo(session_id="s-1", task_ids=["t-1"], created_at=now)
        mock_packager.get_session.return_value = session
        mock_packager.get_task.return_value = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="a",
            name="n1",
            version="0.1",
            source=PluginSource.MARKETPLACE,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        subscribed_queue = None

        def mock_subscribe(sid, queue):
            nonlocal subscribed_queue
            subscribed_queue = queue

        mock_packager.subscribe = mock_subscribe
        mock_packager.unsubscribe = lambda sid, queue: None

        gen = _event_generator("s-1", mock_packager)

        first_event = await gen.__anext__()
        assert first_event["event"] == SSEEventType.SESSION_STARTED

        second_event = await gen.__anext__()
        assert second_event["event"] == SSEEventType.TASK_STARTED

        completed_event = SessionCompletedEvent(
            session_id="s-1",
            success_count=1,
            failed_count=0,
            timestamp=datetime.now(),
        )
        if subscribed_queue:
            subscribed_queue.put_nowait(completed_event)

        final_event = await gen.__anext__()
        assert final_event["event"] == SSEEventType.SESSION_COMPLETED
