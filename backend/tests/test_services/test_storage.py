import pytest

from app.services.storage import StorageService


@pytest.fixture
def storage(tmp_path):
    return StorageService(work_dir=tmp_path)


class TestCreateTaskDirs:
    async def test_creates_three_subdirectories(self, storage, tmp_path):
        result = await storage.create_task_dirs("test-task-id")

        assert (tmp_path / "test-task-id" / "source").is_dir()
        assert (tmp_path / "test-task-id" / "plugin").is_dir()
        assert (tmp_path / "test-task-id" / "output").is_dir()
        assert result == tmp_path / "test-task-id"

    async def test_returns_task_dir_path(self, storage, tmp_path):
        result = await storage.create_task_dirs("test-task-id")
        assert result == tmp_path / "test-task-id"

    async def test_idempotent_creation(self, storage, tmp_path):
        await storage.create_task_dirs("test-task-id")
        await storage.create_task_dirs("test-task-id")

        assert (tmp_path / "test-task-id" / "source").is_dir()


class TestGetTaskDir:
    def test_returns_correct_path(self, storage, tmp_path):
        result = storage.get_task_dir("test-task-id")
        assert result == tmp_path / "test-task-id"


class TestGetSourceDir:
    def test_returns_correct_path(self, storage, tmp_path):
        result = storage.get_source_dir("test-task-id")
        assert result == tmp_path / "test-task-id" / "source"


class TestGetPluginDir:
    def test_returns_correct_path(self, storage, tmp_path):
        result = storage.get_plugin_dir("test-task-id")
        assert result == tmp_path / "test-task-id" / "plugin"


class TestGetOutputDir:
    def test_returns_correct_path(self, storage, tmp_path):
        result = storage.get_output_dir("test-task-id")
        assert result == tmp_path / "test-task-id" / "output"


class TestSavePluginPackage:
    async def test_saves_file_to_source_dir(self, storage, tmp_path):
        await storage.create_task_dirs("task-id")
        result = await storage.save_plugin_package("task-id", b"content", "author-name_0.1.0.difypkg")

        assert result == tmp_path / "task-id" / "source" / "author-name_0.1.0.difypkg"
        assert result.read_bytes() == b"content"

    async def test_sanitizes_path_traversal_filename(self, storage, tmp_path):
        await storage.create_task_dirs("task-id")
        result = await storage.save_plugin_package("task-id", b"content", "../../../etc/passwd")

        assert result.name == "passwd"
        assert result == tmp_path / "task-id" / "source" / "passwd"
        assert result.read_bytes() == b"content"

    async def test_does_not_create_subdirectory_from_filename(self, storage, tmp_path):
        await storage.create_task_dirs("task-id")
        result = await storage.save_plugin_package("task-id", b"content", "author-name_0.1.0.difypkg")

        parent = result.parent
        assert parent == tmp_path / "task-id" / "source"


class TestGetResultFile:
    async def test_returns_path_when_difypkg_exists(self, storage, tmp_path):
        await storage.create_task_dirs("task-id")
        output_dir = tmp_path / "task-id" / "output"
        (output_dir / "agent-0.0.9-offline.difypkg").write_bytes(b"fake-content")

        result = storage.get_result_file("task-id")
        assert result is not None
        assert result.name == "agent-0.0.9-offline.difypkg"

    def test_returns_none_when_no_difypkg_exists(self, storage, tmp_path):
        result = storage.get_result_file("task-id")
        assert result is None

    async def test_returns_none_when_output_dir_is_empty(self, storage, tmp_path):
        await storage.create_task_dirs("task-id")

        result = storage.get_result_file("task-id")
        assert result is None


class TestCleanupTask:
    async def test_deletes_entire_task_directory(self, storage, tmp_path):
        await storage.create_task_dirs("task-id")
        task_dir = tmp_path / "task-id"
        assert task_dir.exists()

        await storage.cleanup_task("task-id")
        assert not task_dir.exists()

    async def test_does_nothing_when_task_dir_does_not_exist(self, storage, tmp_path):
        await storage.cleanup_task("nonexistent-task-id")
