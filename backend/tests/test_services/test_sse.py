import asyncio
from datetime import datetime

import httpx
import pytest

from app.core.config import Settings
from app.models.plugin import PackStep
from app.models.sse import SSEEventType, StepProgressEvent, TaskStartedEvent
from app.services.packager import PackagerService
from app.services.storage import StorageService


@pytest.fixture
def settings(tmp_path):
    return Settings(WORK_DIR=str(tmp_path))


@pytest.fixture
def storage(tmp_path):
    return StorageService(work_dir=tmp_path)


@pytest.fixture
def packager(settings, storage):
    client = httpx.AsyncClient(timeout=30.0)
    return PackagerService(httpx_client=client, settings=settings, storage=storage)


class TestSubscribe:
    async def test_events_are_delivered_to_subscriber(self, packager):
        queue = asyncio.Queue()
        packager.subscribe("s-1", queue)

        event = TaskStartedEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            plugin_version="0.0.9",
            timestamp=datetime.now(),
        )
        packager._emit_event(event)

        received = queue.get_nowait()
        assert received.event_type == SSEEventType.TASK_STARTED
        assert received.task_id == "t-1"

    async def test_multiple_subscribers_receive_events(self, packager):
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        packager.subscribe("s-1", queue1)
        packager.subscribe("s-1", queue2)

        event = TaskStartedEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            plugin_version="0.0.9",
            timestamp=datetime.now(),
        )
        packager._emit_event(event)

        assert queue1.get_nowait().task_id == "t-1"
        assert queue2.get_nowait().task_id == "t-1"


class TestUnsubscribe:
    async def test_unsubscribed_queue_no_longer_receives_events(self, packager):
        queue = asyncio.Queue()
        packager.subscribe("s-1", queue)
        packager.unsubscribe("s-1", queue)

        event = TaskStartedEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            plugin_version="0.0.9",
            timestamp=datetime.now(),
        )
        packager._emit_event(event)

        assert queue.empty()


class TestDifferentSessions:
    async def test_subscribers_only_receive_their_session_events(self, packager):
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        packager.subscribe("s-1", queue1)
        packager.subscribe("s-2", queue2)

        event = TaskStartedEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            plugin_version="0.0.9",
            timestamp=datetime.now(),
        )
        packager._emit_event(event)

        assert queue1.get_nowait().task_id == "t-1"
        assert queue2.empty()


class TestEmitEvent:
    async def test_emit_event_delivers_to_all_session_subscribers(self, packager):
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        packager.subscribe("s-1", queue1)
        packager.subscribe("s-1", queue2)

        event = StepProgressEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            step=PackStep.DOWNLOADING,
            message="正在下载插件包...",
            timestamp=datetime.now(),
        )
        packager._emit_event(event)

        assert queue1.qsize() == 1
        assert queue2.qsize() == 1

    async def test_emit_event_to_nonexistent_session_does_nothing(self, packager):
        event = TaskStartedEvent(
            session_id="nonexistent",
            task_id="t-1",
            plugin_name="agent",
            plugin_version="0.0.9",
            timestamp=datetime.now(),
        )
        packager._emit_event(event)
