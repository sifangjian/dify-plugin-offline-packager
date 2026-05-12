from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import Settings
from app.models.plugin import (
    PackSessionInfo,
    PackStep,
    PackTaskInfo,
    PluginSource,
    TaskStatus,
)
from app.models.sse import (
    STEP_MESSAGES,
    SSEEventType,
    StepProgressEvent,
)
from app.services.packager import PackagerService, PackageStepError
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


class TestEventPushOnTaskStart:
    async def test_task_started_event_pushed(self, packager):
        events = []
        packager._emit_event = lambda e: events.append(e)

        now = datetime.now()
        task = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="a",
            name="n1",
            version="0.1",
            source=PluginSource.MARKETPLACE,
            created_at=now,
            updated_at=now,
        )
        packager._sessions["s-1"] = PackSessionInfo(session_id="s-1", task_ids=["t-1"], created_at=now)
        packager._tasks["t-1"] = task
        packager._pack_marketplace_plugin = AsyncMock()

        await packager._process_task(task)

        started_events = [e for e in events if e.event_type == SSEEventType.TASK_STARTED]
        assert len(started_events) == 1
        assert started_events[0].task_id == "t-1"
        assert started_events[0].plugin_name == "n1"
        assert started_events[0].plugin_version == "0.1"


class TestStepProgressEvents:
    async def test_step_progress_pushed_for_each_step(self, packager):
        events = []

        async def mock_pack(task):
            for step in PackStep:
                task.current_step = step
                packager._emit_event(
                    StepProgressEvent(
                        session_id=task.session_id,
                        task_id=task.task_id,
                        plugin_name=task.name,
                        step=step,
                        message=STEP_MESSAGES[step],
                        timestamp=datetime.now(),
                    )
                )

        packager._emit_event = lambda e: events.append(e)
        packager._pack_marketplace_plugin = mock_pack

        now = datetime.now()
        task = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="a",
            name="n1",
            version="0.1",
            source=PluginSource.MARKETPLACE,
            created_at=now,
            updated_at=now,
        )
        packager._sessions["s-1"] = PackSessionInfo(session_id="s-1", task_ids=["t-1"], created_at=now)
        packager._tasks["t-1"] = task

        await packager._process_task(task)

        step_events = [e for e in events if e.event_type == SSEEventType.STEP_PROGRESS]
        assert len(step_events) == 4
        messages = [e.message for e in step_events]
        assert messages == list(STEP_MESSAGES.values())


class TestTaskSuccessEvent:
    async def test_task_success_event_pushed(self, packager):
        events = []
        packager._emit_event = lambda e: events.append(e)
        packager._pack_marketplace_plugin = AsyncMock()

        now = datetime.now()
        task = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="a",
            name="n1",
            version="0.1",
            source=PluginSource.MARKETPLACE,
            created_at=now,
            updated_at=now,
        )
        packager._sessions["s-1"] = PackSessionInfo(session_id="s-1", task_ids=["t-1"], created_at=now)
        packager._tasks["t-1"] = task

        await packager._process_task(task)

        success_events = [e for e in events if e.event_type == SSEEventType.TASK_SUCCESS]
        assert len(success_events) == 1
        assert success_events[0].task_id == "t-1"
        assert success_events[0].plugin_name == "n1"
        assert success_events[0].plugin_version == "0.1"


class TestTaskFailedEvent:
    async def test_task_failed_event_pushed(self, packager):
        events = []

        async def mock_fail(task):
            raise PackageStepError(
                step=PackStep.DOWNLOADING,
                message="下载插件包失败",
                raw_error="timeout",
            )

        packager._emit_event = lambda e: events.append(e)
        packager._pack_marketplace_plugin = mock_fail

        now = datetime.now()
        task = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="a",
            name="n1",
            version="0.1",
            source=PluginSource.MARKETPLACE,
            created_at=now,
            updated_at=now,
        )
        packager._sessions["s-1"] = PackSessionInfo(session_id="s-1", task_ids=["t-1"], created_at=now)
        packager._tasks["t-1"] = task

        await packager._process_task(task)

        failed_events = [e for e in events if e.event_type == SSEEventType.TASK_FAILED]
        assert len(failed_events) == 1
        assert failed_events[0].step == PackStep.DOWNLOADING
        assert failed_events[0].message == "下载插件包失败"
        assert failed_events[0].raw_error == "timeout"


class TestSessionCompletedEvent:
    async def test_session_completed_event_pushed(self, packager):
        now = datetime.now()
        session = PackSessionInfo(session_id="s-1", task_ids=["t-1", "t-2"], created_at=now)
        packager._sessions["s-1"] = session

        task1 = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="a",
            name="n1",
            version="0.1",
            source=PluginSource.MARKETPLACE,
            status=TaskStatus.SUCCESS,
            created_at=now,
            updated_at=now,
        )
        task2 = PackTaskInfo(
            task_id="t-2",
            session_id="s-1",
            author="b",
            name="n2",
            version="0.2",
            source=PluginSource.MARKETPLACE,
            status=TaskStatus.FAILED,
            created_at=now,
            updated_at=now,
        )
        packager._tasks["t-1"] = task1
        packager._tasks["t-2"] = task2

        events = []
        packager._emit_event = lambda e: events.append(e)

        packager._check_session_completion("s-1")

        completed_events = [e for e in events if e.event_type == SSEEventType.SESSION_COMPLETED]
        assert len(completed_events) == 1
        assert completed_events[0].success_count == 1
        assert completed_events[0].failed_count == 1
