import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.plugin import Architecture, PackStep, PackTaskInfo, PluginSource, TaskStatus
from app.services.packager import PackageStepError, PackagerService
from app.services.storage import StorageService


@pytest.fixture
def mock_settings():
    return Settings()


@pytest.fixture
def mock_storage():
    storage = MagicMock(spec=StorageService)
    storage.get_source_dir.return_value = MagicMock()
    storage.get_plugin_dir.return_value = MagicMock()
    storage.get_output_dir.return_value = MagicMock()
    return storage


@pytest.fixture
def mock_httpx_client():
    return AsyncMock()


@pytest.fixture
def packager(mock_httpx_client, mock_settings, mock_storage):
    service = PackagerService(
        httpx_client=mock_httpx_client,
        settings=mock_settings,
        storage=mock_storage,
    )
    return service


def create_task(architecture: Architecture = Architecture.LINUX_AMD64) -> PackTaskInfo:
    return PackTaskInfo(
        task_id="t-1",
        session_id="s-1",
        author="langgenius",
        name="agent",
        version="0.0.9",
        source=PluginSource.MARKETPLACE,
        architecture=architecture,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


class TestPipDownloadArchitecture:
    def test_linux_amd64_includes_manylinux2014_x86_64(self, packager):
        task = create_task(Architecture.LINUX_AMD64)
        cmd = packager._build_pip_download_cmd(task, "/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--platform" in cmd
        assert "manylinux2014_x86_64" in cmd

    def test_linux_arm64_includes_manylinux2014_aarch64(self, packager):
        task = create_task(Architecture.LINUX_ARM64)
        cmd = packager._build_pip_download_cmd(task, "/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--platform" in cmd
        assert "manylinux2014_aarch64" in cmd

    def test_darwin_amd64_includes_macosx_10_9_x86_64(self, packager):
        task = create_task(Architecture.DARWIN_AMD64)
        cmd = packager._build_pip_download_cmd(task, "/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--platform" in cmd
        assert "macosx_10_9_x86_64" in cmd

    def test_darwin_arm64_includes_macosx_11_0_arm64(self, packager):
        task = create_task(Architecture.DARWIN_ARM64)
        cmd = packager._build_pip_download_cmd(task, "/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--platform" in cmd
        assert "macosx_11_0_arm64" in cmd

    def test_includes_only_binary_flag(self, packager):
        task = create_task(Architecture.LINUX_AMD64)
        cmd = packager._build_pip_download_cmd(task, "/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--only-binary=:all:" in cmd


class TestStepPackageArchitecture:
    def test_linux_amd64_uses_correct_cli_path(self, packager, mock_settings):
        task = create_task(Architecture.LINUX_AMD64)
        cli_path = packager._get_cli_path(task)
        assert cli_path == mock_settings.get_cli_path(Architecture.LINUX_AMD64)

    def test_linux_arm64_uses_correct_cli_path(self, packager, mock_settings):
        task = create_task(Architecture.LINUX_ARM64)
        cli_path = packager._get_cli_path(task)
        assert cli_path == mock_settings.get_cli_path(Architecture.LINUX_ARM64)

    def test_darwin_amd64_uses_correct_cli_path(self, packager, mock_settings):
        task = create_task(Architecture.DARWIN_AMD64)
        cli_path = packager._get_cli_path(task)
        assert cli_path == mock_settings.get_cli_path(Architecture.DARWIN_AMD64)

    def test_darwin_arm64_uses_correct_cli_path(self, packager, mock_settings):
        task = create_task(Architecture.DARWIN_ARM64)
        cli_path = packager._get_cli_path(task)
        assert cli_path == mock_settings.get_cli_path(Architecture.DARWIN_ARM64)


class TestArchitectureExceptionHandling:
    def test_pip_download_no_matching_distribution_error(self, packager):
        error_output = b"ERROR: No matching distribution found for flask"
        with pytest.raises(PackageStepError) as exc_info:
            packager._parse_pip_download_error(error_output, Architecture.LINUX_ARM64)
        assert "flask" in exc_info.value.message
        assert "linux-arm64" in exc_info.value.message

    def test_pip_download_generic_error(self, packager):
        error_output = b"ERROR: Connection timeout"
        with pytest.raises(PackageStepError) as exc_info:
            packager._parse_pip_download_error(error_output, Architecture.LINUX_AMD64)
        assert "下载依赖包失败" in exc_info.value.message

    def test_cli_path_not_exists_error(self, packager):
        task = create_task(Architecture.LINUX_ARM64)
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(PackageStepError) as exc_info:
                packager._validate_cli_path(task)
            assert "CLI 工具不存在" in exc_info.value.message
