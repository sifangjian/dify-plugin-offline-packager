from datetime import datetime

from app.models.plugin import (
    PackPluginItem,
    PackRequest,
    PackResponse,
    PackSessionInfo,
    PackStep,
    PackTaskInfo,
    PackTaskSummary,
    PluginSource,
    SessionStatus,
    TaskStatus,
)


class TestPluginSource:
    def test_has_marketplace_value(self):
        assert PluginSource.MARKETPLACE == "marketplace"

    def test_has_local_value(self):
        assert PluginSource.LOCAL == "local"

    def test_has_exactly_two_values(self):
        assert len(PluginSource) == 2


class TestTaskStatus:
    def test_has_pending_value(self):
        assert TaskStatus.PENDING == "pending"

    def test_has_running_value(self):
        assert TaskStatus.RUNNING == "running"

    def test_has_success_value(self):
        assert TaskStatus.SUCCESS == "success"

    def test_has_failed_value(self):
        assert TaskStatus.FAILED == "failed"

    def test_has_cancelled_value(self):
        assert TaskStatus.CANCELLED == "cancelled"

    def test_has_exactly_five_values(self):
        assert len(TaskStatus) == 5


class TestPackStep:
    def test_has_downloading_value(self):
        assert PackStep.DOWNLOADING == "downloading"

    def test_has_resolving_deps_value(self):
        assert PackStep.RESOLVING_DEPS == "resolving_deps"

    def test_has_downloading_deps_value(self):
        assert PackStep.DOWNLOADING_DEPS == "downloading_deps"

    def test_has_packaging_value(self):
        assert PackStep.PACKAGING == "packaging"

    def test_has_exactly_four_values(self):
        assert len(PackStep) == 4


class TestPackPluginItem:
    def test_instantiation_with_required_fields(self):
        item = PackPluginItem(author="langgenius", name="agent", version="0.0.9")
        assert item.author == "langgenius"
        assert item.name == "agent"
        assert item.version == "0.0.9"

    def test_source_defaults_to_marketplace(self):
        item = PackPluginItem(author="langgenius", name="agent", version="0.0.9")
        assert item.source == PluginSource.MARKETPLACE

    def test_source_can_be_set_to_local(self):
        item = PackPluginItem(author="langgenius", name="agent", version="0.0.9", source=PluginSource.LOCAL)
        assert item.source == PluginSource.LOCAL


class TestPackRequest:
    def test_instantiation_with_plugins(self):
        request = PackRequest(plugins=[PackPluginItem(author="langgenius", name="agent", version="0.0.9")])
        assert len(request.plugins) == 1
        assert request.plugins[0].author == "langgenius"

    def test_with_multiple_plugins(self):
        request = PackRequest(
            plugins=[
                PackPluginItem(author="a", name="n1", version="0.1"),
                PackPluginItem(author="b", name="n2", version="0.2"),
            ]
        )
        assert len(request.plugins) == 2


class TestPackTaskSummary:
    def test_instantiation(self):
        summary = PackTaskSummary(
            task_id="t-1", author="langgenius", name="agent", version="0.0.9", status=TaskStatus.PENDING
        )
        assert summary.task_id == "t-1"
        assert summary.author == "langgenius"
        assert summary.name == "agent"
        assert summary.version == "0.0.9"
        assert summary.status == TaskStatus.PENDING


class TestPackResponse:
    def test_instantiation(self):
        response = PackResponse(
            session_id="s-1",
            tasks=[PackTaskSummary(task_id="t-1", author="a", name="n1", version="0.1", status=TaskStatus.PENDING)],
        )
        assert response.session_id == "s-1"
        assert len(response.tasks) == 1


class TestPackTaskInfo:
    def test_instantiation_with_required_fields(self):
        now = datetime.now()
        task = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="langgenius",
            name="agent",
            version="0.0.9",
            source=PluginSource.MARKETPLACE,
            created_at=now,
            updated_at=now,
        )
        assert task.task_id == "t-1"
        assert task.session_id == "s-1"
        assert task.author == "langgenius"
        assert task.name == "agent"
        assert task.version == "0.0.9"
        assert task.source == PluginSource.MARKETPLACE
        assert task.status == TaskStatus.PENDING
        assert task.current_step is None
        assert task.error_message is None
        assert task.raw_error is None
        assert task.result_file_path is None
        assert task.local_file_path is None

    def test_json_serialization(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        task = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="langgenius",
            name="agent",
            version="0.0.9",
            source=PluginSource.MARKETPLACE,
            created_at=now,
            updated_at=now,
        )
        data = task.model_dump(mode="json")
        assert data["task_id"] == "t-1"
        assert data["status"] == "pending"
        assert data["source"] == "marketplace"


class TestSessionStatus:
    def test_has_active_value(self):
        assert SessionStatus.ACTIVE == "active"

    def test_has_completed_value(self):
        assert SessionStatus.COMPLETED == "completed"


class TestPackSessionInfo:
    def test_instantiation(self):
        now = datetime.now()
        session = PackSessionInfo(session_id="s-1", task_ids=["t-1", "t-2"], created_at=now)
        assert session.session_id == "s-1"
        assert len(session.task_ids) == 2
        assert session.status == SessionStatus.ACTIVE

    def test_json_serialization(self):
        now = datetime(2025, 1, 1, 0, 0, 0)
        session = PackSessionInfo(session_id="s-1", task_ids=["t-1"], created_at=now)
        data = session.model_dump(mode="json")
        assert data["session_id"] == "s-1"
        assert data["status"] == "active"
