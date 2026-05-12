import httpx
import pytest

from app.core.config import Settings
from app.models.plugin import (
    PackPluginItem,
    SessionStatus,
    TaskStatus,
)
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


class TestCancelSession:
    async def test_marks_pending_tasks_as_cancelled(self, packager):
        plugins = [
            PackPluginItem(author="a", name="n1", version="0.1"),
            PackPluginItem(author="b", name="n2", version="0.2"),
        ]
        session = await packager.submit_session(plugins)

        result = await packager.cancel_session(session.session_id)

        assert result is True
        for task_id in session.task_ids:
            task = packager.get_task(task_id)
            assert task.status == TaskStatus.CANCELLED

    async def test_marks_running_tasks_as_cancelled(self, packager):
        plugins = [PackPluginItem(author="a", name="n1", version="0.1")]
        session = await packager.submit_session(plugins)

        task_id = session.task_ids[0]
        packager._tasks[task_id].status = TaskStatus.RUNNING

        result = await packager.cancel_session(session.session_id)

        assert result is True
        task = packager.get_task(task_id)
        assert task.status == TaskStatus.CANCELLED

    async def test_does_not_affect_success_tasks(self, packager):
        plugins = [
            PackPluginItem(author="a", name="n1", version="0.1"),
            PackPluginItem(author="b", name="n2", version="0.2"),
        ]
        session = await packager.submit_session(plugins)

        packager._tasks[session.task_ids[0]].status = TaskStatus.SUCCESS
        packager._tasks[session.task_ids[1]].status = TaskStatus.RUNNING

        await packager.cancel_session(session.session_id)

        assert packager.get_task(session.task_ids[0]).status == TaskStatus.SUCCESS
        assert packager.get_task(session.task_ids[1]).status == TaskStatus.CANCELLED

    async def test_returns_false_for_nonexistent_session(self, packager):
        result = await packager.cancel_session("nonexistent")
        assert result is False

    async def test_session_status_set_to_completed(self, packager):
        plugins = [PackPluginItem(author="a", name="n1", version="0.1")]
        session = await packager.submit_session(plugins)

        await packager.cancel_session(session.session_id)

        updated_session = packager.get_session(session.session_id)
        assert updated_session.status == SessionStatus.COMPLETED
