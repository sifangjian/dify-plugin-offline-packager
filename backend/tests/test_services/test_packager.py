import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.models.plugin import (
    PackPluginItem,
    PackSessionInfo,
    PackStep,
    PackTaskInfo,
    PluginSource,
    SessionStatus,
    TaskStatus,
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


class TestSubmitSession:
    async def test_returns_session_with_session_id(self, packager):
        plugins = [PackPluginItem(author="a", name="n1", version="0.1")]
        session = await packager.submit_session(plugins)

        assert session.session_id is not None
        assert len(session.session_id) > 0

    async def test_returns_session_with_two_task_ids(self, packager):
        plugins = [
            PackPluginItem(author="a", name="n1", version="0.1"),
            PackPluginItem(author="b", name="n2", version="0.2"),
        ]
        session = await packager.submit_session(plugins)

        assert len(session.task_ids) == 2

    async def test_tasks_are_pending(self, packager):
        plugins = [PackPluginItem(author="a", name="n1", version="0.1")]
        session = await packager.submit_session(plugins)

        for task_id in session.task_ids:
            task = packager.get_task(task_id)
            assert task.status == TaskStatus.PENDING

    async def test_tasks_in_internal_dict(self, packager):
        plugins = [PackPluginItem(author="a", name="n1", version="0.1")]
        session = await packager.submit_session(plugins)

        for task_id in session.task_ids:
            assert task_id in packager._tasks

    async def test_queue_has_tasks_waiting(self, packager):
        plugins = [
            PackPluginItem(author="a", name="n1", version="0.1"),
            PackPluginItem(author="b", name="n2", version="0.2"),
        ]
        await packager.submit_session(plugins)

        assert packager._queue.qsize() == 2


class TestGetSession:
    async def test_returns_correct_session(self, packager):
        plugins = [PackPluginItem(author="a", name="n1", version="0.1")]
        session = await packager.submit_session(plugins)

        result = packager.get_session(session.session_id)
        assert result is not None
        assert result.session_id == session.session_id

    async def test_returns_none_for_nonexistent(self, packager):
        result = packager.get_session("nonexistent")
        assert result is None


class TestGetTask:
    async def test_returns_correct_task(self, packager):
        plugins = [PackPluginItem(author="a", name="n1", version="0.1")]
        session = await packager.submit_session(plugins)

        task_id = session.task_ids[0]
        task = packager.get_task(task_id)
        assert task is not None
        assert task.author == "a"
        assert task.name == "n1"
        assert task.version == "0.1"

    async def test_returns_none_for_nonexistent(self, packager):
        result = packager.get_task("nonexistent")
        assert result is None


class TestQueueConsumer:
    async def test_processes_tasks_sequentially(self, packager):
        processed = []

        async def mock_process(task):
            processed.append(task.task_id)

        packager._process_task = mock_process
        packager.start()

        plugins = [
            PackPluginItem(author="a", name="n1", version="0.1"),
            PackPluginItem(author="b", name="n2", version="0.2"),
        ]
        await packager.submit_session(plugins)

        await asyncio.sleep(0.1)
        await packager.stop()

        assert len(processed) == 2

    async def test_continues_after_task_failure(self, packager):
        processed = []

        async def mock_process(task):
            if task.name == "n1":
                raise PackageStepError(step=PackStep.DOWNLOADING, message="下载插件包失败", raw_error="timeout")
            processed.append(task.task_id)

        packager._process_task = mock_process
        packager.start()

        plugins = [
            PackPluginItem(author="a", name="n1", version="0.1"),
            PackPluginItem(author="b", name="n2", version="0.2"),
        ]
        await packager.submit_session(plugins)

        await asyncio.sleep(0.1)
        await packager.stop()

        assert len(processed) == 1


class TestCheckSessionCompletion:
    async def test_marks_session_completed_when_all_tasks_done(self, packager):
        plugins = [
            PackPluginItem(author="a", name="n1", version="0.1"),
            PackPluginItem(author="b", name="n2", version="0.2"),
        ]
        session = await packager.submit_session(plugins)

        for task_id in session.task_ids:
            packager._tasks[task_id].status = TaskStatus.SUCCESS

        packager._check_session_completion(session.session_id)

        updated_session = packager.get_session(session.session_id)
        assert updated_session.status == SessionStatus.COMPLETED


class TestPackageStepError:
    def test_instantiation(self):
        error = PackageStepError(step=PackStep.DOWNLOADING, message="下载插件包失败", raw_error="timeout")
        assert error.step == PackStep.DOWNLOADING
        assert error.message == "下载插件包失败"
        assert error.raw_error == "timeout"

    def test_is_exception(self):
        error = PackageStepError(step=PackStep.DOWNLOADING, message="test", raw_error="err")
        assert isinstance(error, Exception)


class TestProcessTaskSourceDispatch:
    async def test_marketplace_source_calls_pack_marketplace(self, packager):
        called_with = []

        async def mock_pack_marketplace(task):
            called_with.append(task.task_id)

        packager._pack_marketplace_plugin = mock_pack_marketplace
        packager._pack_local_plugin = AsyncMock()

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

        assert len(called_with) == 1

    async def test_local_source_calls_pack_local(self, packager):
        called_with = []

        async def mock_pack_local(task):
            called_with.append(task.task_id)

        packager._pack_marketplace_plugin = AsyncMock()
        packager._pack_local_plugin = mock_pack_local

        now = datetime.now()
        task = PackTaskInfo(
            task_id="t-1",
            session_id="s-1",
            author="a",
            name="n1",
            version="0.1",
            source=PluginSource.LOCAL,
            created_at=now,
            updated_at=now,
        )
        packager._sessions["s-1"] = PackSessionInfo(session_id="s-1", task_ids=["t-1"], created_at=now)
        packager._tasks["t-1"] = task

        await packager._process_task(task)

        assert len(called_with) == 1

    async def test_success_sets_task_status_to_success(self, packager):
        packager._pack_marketplace_plugin = AsyncMock()
        packager._emit_event = lambda event: None

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

        assert task.status == TaskStatus.SUCCESS

    async def test_failure_sets_task_status_to_failed(self, packager):
        async def mock_pack_fail(task):
            raise PackageStepError(step=PackStep.DOWNLOADING, message="下载插件包失败", raw_error="timeout")

        packager._pack_marketplace_plugin = mock_pack_fail
        packager._emit_event = lambda event: None

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

        assert task.status == TaskStatus.FAILED
        assert task.error_message == "下载插件包失败"
        assert task.raw_error == "timeout"
        assert task.current_step == PackStep.DOWNLOADING


def _make_task(packager, task_id="t-1", session_id="s-1", **kwargs):
    now = datetime.now()
    defaults = dict(
        task_id=task_id,
        session_id=session_id,
        author="a",
        name="n1",
        version="0.1",
        source=PluginSource.MARKETPLACE,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    task = PackTaskInfo(**defaults)
    packager._sessions[session_id] = PackSessionInfo(session_id=session_id, task_ids=[task_id], created_at=now)
    packager._tasks[task_id] = task
    return task


class TestStepDownload:
    async def test_sets_current_step_to_downloading(self, packager, storage):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        packager._marketplace.download_plugin = AsyncMock(return_value=httpx.Response(200, content=b"fake"))
        await storage.create_task_dirs(task.task_id)

        await packager._step_download(task)
        assert task.current_step == PackStep.DOWNLOADING

    async def test_calls_marketplace_download(self, packager, storage):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        packager._marketplace.download_plugin = AsyncMock(return_value=httpx.Response(200, content=b"fake"))
        await storage.create_task_dirs(task.task_id)

        await packager._step_download(task)
        packager._marketplace.download_plugin.assert_awaited_once_with(author="a", name="n1", version="0.1")

    async def test_saves_file_to_source_dir(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        packager._marketplace.download_plugin = AsyncMock(return_value=httpx.Response(200, content=b"fake-content"))

        await storage.create_task_dirs(task.task_id)
        await packager._step_download(task)

        source_dir = storage.get_source_dir(task.task_id)
        saved_file = source_dir / "a-n1_0.1.difypkg"
        assert saved_file.exists()
        assert saved_file.read_bytes() == b"fake-content"

    async def test_raises_error_on_download_failure(self, packager):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        packager._marketplace.download_plugin = AsyncMock(side_effect=Exception("timeout"))

        with pytest.raises(PackageStepError) as exc_info:
            await packager._step_download(task)

        assert exc_info.value.step == PackStep.DOWNLOADING
        assert exc_info.value.message == "下载插件包失败"
        assert "timeout" in exc_info.value.raw_error


class TestStepResolveDeps:
    async def test_sets_current_step_to_resolving_deps(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        source_dir = storage.get_source_dir(task.task_id)

        import zipfile

        zf_path = source_dir / "test.difypkg"
        with zipfile.ZipFile(zf_path, "w") as zf:
            zf.writestr("pyproject.toml", "[project]\nname='test'\n")
            zf.writestr("requirements.txt", "flask==2.0\n")

        await packager._step_resolve_deps(task)
        assert task.current_step == PackStep.RESOLVING_DEPS

    async def test_extracts_difypkg_to_plugin_dir(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        source_dir = storage.get_source_dir(task.task_id)
        plugin_dir = storage.get_plugin_dir(task.task_id)

        import zipfile

        zf_path = source_dir / "test.difypkg"
        with zipfile.ZipFile(zf_path, "w") as zf:
            zf.writestr("pyproject.toml", "[project]\nname='test'\n")
            zf.writestr("requirements.txt", "flask==2.0\n")

        await packager._step_resolve_deps(task)
        assert (plugin_dir / "pyproject.toml").exists()
        assert (plugin_dir / "requirements.txt").exists()

    async def test_has_both_files_skips_uv(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        source_dir = storage.get_source_dir(task.task_id)

        import zipfile

        zf_path = source_dir / "test.difypkg"
        with zipfile.ZipFile(zf_path, "w") as zf:
            zf.writestr("pyproject.toml", "[project]\nname='test'\n")
            zf.writestr("requirements.txt", "flask==2.0\n")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            await packager._step_resolve_deps(task)
            mock_exec.assert_not_called()

    async def test_no_dep_files_raises_error(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        source_dir = storage.get_source_dir(task.task_id)

        import zipfile

        zf_path = source_dir / "test.difypkg"
        with zipfile.ZipFile(zf_path, "w") as zf:
            zf.writestr("README.md", "hello")

        with pytest.raises(PackageStepError) as exc_info:
            await packager._step_resolve_deps(task)

        assert exc_info.value.step == PackStep.RESOLVING_DEPS
        assert exc_info.value.message == "插件缺少依赖定义文件"


class TestStepDownloadDeps:
    async def test_sets_current_step_to_downloading_deps(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")

        with patch.object(packager, "_run_subprocess_with_progress", return_value=(0, b"")):
            await packager._step_download_deps(task)

        assert task.current_step == PackStep.DOWNLOADING_DEPS

    async def test_creates_wheels_dir(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")

        with patch.object(packager, "_run_subprocess_with_progress", return_value=(0, b"")):
            await packager._step_download_deps(task)

        assert (plugin_dir / "wheels").is_dir()

    async def test_uses_list_args_for_subprocess(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")

        mock_run = AsyncMock(return_value=(0, b""))
        with patch.object(packager, "_run_subprocess_with_progress", mock_run):
            await packager._step_download_deps(task)

        call_args = mock_run.call_args
        cmd = call_args[0][1]
        assert cmd[0] == "python3"
        assert cmd[1] == "-m"
        assert cmd[2] == "pip"

    async def test_raises_error_on_pip_failure(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")

        with (
            patch.object(packager, "_run_subprocess_with_progress", return_value=(1, b"pip error")),
            pytest.raises(PackageStepError) as exc_info,
        ):
            await packager._step_download_deps(task)

        assert exc_info.value.step == PackStep.DOWNLOADING_DEPS
        assert exc_info.value.message == "下载依赖包失败"


class TestStepPackage:
    async def test_sets_current_step_to_packaging(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")
        (plugin_dir / "pyproject.toml").write_text("[project]\nname='test'\n")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await packager._step_package(task)

        assert task.current_step == PackStep.PACKAGING

    async def test_injects_no_index_into_requirements(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")
        (plugin_dir / "pyproject.toml").write_text("[project]\nname='test'\n")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await packager._step_package(task)

        content = (plugin_dir / "requirements.txt").read_text()
        assert content.startswith("--no-index\n--find-links=./wheels\n")

    async def test_injects_uv_config_into_pyproject(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")
        (plugin_dir / "pyproject.toml").write_text("[project]\nname='test'\n")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await packager._step_package(task)

        content = (plugin_dir / "pyproject.toml").read_text()
        assert "[tool.uv]" in content
        assert "no-index = true" in content

    async def test_does_not_duplicate_uv_config(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")
        (plugin_dir / "pyproject.toml").write_text("[project]\nname='test'\n[tool.uv]\nno-index = true\n")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await packager._step_package(task)

        content = (plugin_dir / "pyproject.toml").read_text()
        assert content.count("[tool.uv]") == 1

    async def test_calls_cli_with_correct_args(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await packager._step_package(task)

        call_args = mock_exec.call_args
        cmd = call_args[0]
        assert cmd[0] == packager._settings.DIFY_PLUGIN_CLI_PATH
        assert cmd[1] == "plugin"
        assert cmd[2] == "package"

    async def test_sets_result_file_path_on_success(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await packager._step_package(task)

        assert task.result_file_path is not None
        assert "offline.difypkg" in str(task.result_file_path)

    async def test_raises_error_on_cli_failure(self, packager, storage, tmp_path):
        task = _make_task(packager)
        packager._emit_event = lambda event: None
        await storage.create_task_dirs(task.task_id)

        plugin_dir = storage.get_plugin_dir(task.task_id)
        (plugin_dir / "requirements.txt").write_text("flask==2.0\n")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"cli error"))
        mock_proc.returncode = 1

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            pytest.raises(PackageStepError) as exc_info,
        ):
            await packager._step_package(task)

        assert exc_info.value.step == PackStep.PACKAGING
        assert exc_info.value.message == "打包离线插件失败"
