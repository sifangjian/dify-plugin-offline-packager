from datetime import datetime

from app.models.plugin import PackStep
from app.models.sse import (
    STEP_MESSAGES,
    SessionCompletedEvent,
    SessionStartedEvent,
    SSEEventType,
    StepProgressEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    TaskSuccessEvent,
)


class TestSSEEventType:
    def test_has_session_started(self):
        assert SSEEventType.SESSION_STARTED == "session_started"

    def test_has_task_started(self):
        assert SSEEventType.TASK_STARTED == "task_started"

    def test_has_step_progress(self):
        assert SSEEventType.STEP_PROGRESS == "step_progress"

    def test_has_task_success(self):
        assert SSEEventType.TASK_SUCCESS == "task_success"

    def test_has_task_failed(self):
        assert SSEEventType.TASK_FAILED == "task_failed"

    def test_has_session_completed(self):
        assert SSEEventType.SESSION_COMPLETED == "session_completed"

    def test_has_exactly_six_values(self):
        assert len(SSEEventType) == 6


class TestStepMessages:
    def test_downloading_message(self):
        assert STEP_MESSAGES[PackStep.DOWNLOADING] == "正在下载插件包..."

    def test_resolving_deps_message(self):
        assert STEP_MESSAGES[PackStep.RESOLVING_DEPS] == "正在解析依赖..."

    def test_downloading_deps_message(self):
        assert STEP_MESSAGES[PackStep.DOWNLOADING_DEPS] == "正在下载依赖包..."

    def test_packaging_message(self):
        assert STEP_MESSAGES[PackStep.PACKAGING] == "正在打包离线插件..."

    def test_maps_all_four_steps(self):
        assert len(STEP_MESSAGES) == 4


class TestSessionStartedEvent:
    def test_instantiation(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = SessionStartedEvent(session_id="s-1", total=3, timestamp=now)
        assert event.event_type == SSEEventType.SESSION_STARTED
        assert event.session_id == "s-1"
        assert event.total == 3

    def test_json_serialization(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = SessionStartedEvent(session_id="s-1", total=3, timestamp=now)
        data = event.model_dump(mode="json")
        assert data["event_type"] == "session_started"
        assert data["session_id"] == "s-1"
        assert data["total"] == 3


class TestTaskStartedEvent:
    def test_instantiation(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = TaskStartedEvent(
            session_id="s-1", task_id="t-1", plugin_name="agent", plugin_version="0.0.9", timestamp=now
        )
        assert event.event_type == SSEEventType.TASK_STARTED
        assert event.task_id == "t-1"
        assert event.plugin_name == "agent"
        assert event.plugin_version == "0.0.9"

    def test_json_serialization(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = TaskStartedEvent(
            session_id="s-1", task_id="t-1", plugin_name="agent", plugin_version="0.0.9", timestamp=now
        )
        data = event.model_dump(mode="json")
        assert data["event_type"] == "task_started"


class TestStepProgressEvent:
    def test_instantiation(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = StepProgressEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            step=PackStep.DOWNLOADING,
            message="正在下载插件包...",
            timestamp=now,
        )
        assert event.event_type == SSEEventType.STEP_PROGRESS
        assert event.step == PackStep.DOWNLOADING
        assert event.message == "正在下载插件包..."

    def test_json_serialization(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = StepProgressEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            step=PackStep.DOWNLOADING,
            message="正在下载插件包...",
            timestamp=now,
        )
        data = event.model_dump(mode="json")
        assert data["step"] == "downloading"


class TestTaskSuccessEvent:
    def test_instantiation(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = TaskSuccessEvent(
            session_id="s-1", task_id="t-1", plugin_name="agent", plugin_version="0.0.9", timestamp=now
        )
        assert event.event_type == SSEEventType.TASK_SUCCESS
        assert event.task_id == "t-1"
        assert event.plugin_name == "agent"

    def test_json_serialization(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = TaskSuccessEvent(
            session_id="s-1", task_id="t-1", plugin_name="agent", plugin_version="0.0.9", timestamp=now
        )
        data = event.model_dump(mode="json")
        assert data["event_type"] == "task_success"


class TestTaskFailedEvent:
    def test_instantiation(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = TaskFailedEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            step=PackStep.DOWNLOADING,
            message="下载插件包失败",
            raw_error="timeout",
            timestamp=now,
        )
        assert event.event_type == SSEEventType.TASK_FAILED
        assert event.step == PackStep.DOWNLOADING
        assert event.message == "下载插件包失败"
        assert event.raw_error == "timeout"

    def test_json_serialization(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = TaskFailedEvent(
            session_id="s-1",
            task_id="t-1",
            plugin_name="agent",
            step=PackStep.DOWNLOADING,
            message="下载插件包失败",
            raw_error="timeout",
            timestamp=now,
        )
        data = event.model_dump(mode="json")
        assert data["event_type"] == "task_failed"
        assert data["step"] == "downloading"
        assert data["message"] == "下载插件包失败"
        assert data["raw_error"] == "timeout"


class TestSessionCompletedEvent:
    def test_instantiation(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = SessionCompletedEvent(session_id="s-1", success_count=2, failed_count=1, timestamp=now)
        assert event.event_type == SSEEventType.SESSION_COMPLETED
        assert event.success_count == 2
        assert event.failed_count == 1

    def test_json_serialization(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        event = SessionCompletedEvent(session_id="s-1", success_count=2, failed_count=1, timestamp=now)
        data = event.model_dump(mode="json")
        assert data["event_type"] == "session_completed"
        assert data["success_count"] == 2
        assert data["failed_count"] == 1
