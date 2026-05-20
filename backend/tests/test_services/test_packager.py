from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.plugin import Architecture, PackTaskInfo, PluginSource
from app.services.packager import PackagerService, PackageStepError
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


class TestPipDownloadCmdNoPlatform:
    def test_no_platform_flag(self, packager):
        cmd = packager._build_pip_download_cmd_no_platform("/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--platform" not in cmd

    def test_no_only_binary_flag(self, packager):
        cmd = packager._build_pip_download_cmd_no_platform("/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--only-binary=:all:" not in cmd

    def test_includes_prefer_binary(self, packager):
        cmd = packager._build_pip_download_cmd_no_platform("/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--prefer-binary" in cmd

    def test_includes_index_url(self, packager):
        cmd = packager._build_pip_download_cmd_no_platform("/tmp/req.txt", "/tmp/wheels", "https://mirrors.aliyun.com/pypi/simple")
        assert "--index-url" in cmd
        assert "https://mirrors.aliyun.com/pypi/simple" in cmd


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


class TestPatchRequirements:
    def test_patch_exact_version(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("greenlet==3.3.0\n")
        packager._patch_requirements(req_file)
        assert req_file.read_text() == "greenlet>=3.2.0\n"

    def test_patch_compatible_version(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("greenlet~=3.3.0\n")
        packager._patch_requirements(req_file)
        assert req_file.read_text() == "greenlet~=3.2.0\n"

    def test_remove_dependency(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("xhtml2pdf==0.2.17\nflask==3.0.3\n")
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "xhtml2pdf" not in content
        assert "flask>=3.0.0" in content

    def test_preserve_hash_when_no_patch(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("unknown-pkg==1.0.0 --hash=sha256:abc123\n")
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "unknown-pkg==1.0.0" in content
        assert "--hash=sha256:abc123" in content

    def test_preserve_unknown_package(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("unknown-pkg==1.0.0\n")
        packager._patch_requirements(req_file)
        assert req_file.read_text() == "unknown-pkg==1.0.0\n"

    def test_preserve_comments_and_options(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        original = "# this is a comment\n--index-url https://pypi.org/simple\nflask==3.0.3\n"
        req_file.write_text(original)
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "# this is a comment" in content
        assert "--index-url https://pypi.org/simple" in content

    def test_patch_package_with_extras(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("pandas[output_formatting]~=3.0.1\n")
        packager._patch_requirements(req_file)
        assert req_file.read_text() == "pandas>=2.2.0\n"

    def test_no_file_no_error(self, packager):
        packager._patch_requirements(Path("/nonexistent/file.txt"))

    def test_multiple_patches_in_one_file(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("greenlet==3.3.0\nflask~=3.0.3\nunknown-pkg==1.0.0\n")
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "greenlet>=3.2.0" in content
        assert "flask~=3.0.0" in content
        assert "unknown-pkg==1.0.0" in content

    def test_greenlet_330_replaced(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("greenlet==3.3.0\nflask==2.3.2\nrequests==2.32.0\n")
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "greenlet==3.3.0" not in content
        assert "greenlet>=3.2.0" in content
        assert "flask==2.3.2" in content
        assert "requests==2.32.0" in content

    def test_patch_with_environment_marker(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("greenlet==3.3.0 ; python_version>='3.8'\n")
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "greenlet==3.3.0" not in content
        assert "greenlet>=3.2.0" in content
        assert "python_version>='3.8'" in content

    def test_patch_with_hash(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("greenlet==3.3.0 --hash=sha256:abc123\n")
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "greenlet==3.3.0" not in content
        assert "greenlet>=3.2.0" in content
        assert "--hash" not in content

    def test_patch_uv_export_multiline_format(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("greenlet==3.3.0 \\\n    --hash=sha256:abc123 \\\n    --hash=sha256:def456\nflask==3.0.3\n")
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "greenlet==3.3.0" not in content
        assert "greenlet>=3.2.0" in content
        assert "--hash" not in content
        assert "flask>=3.0.0" in content

    def test_remove_with_environment_marker(self, packager, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("xhtml2pdf==0.2.17 ; python_version>='3.8'\nflask==3.0.3\n")
        packager._patch_requirements(req_file)
        content = req_file.read_text()
        assert "xhtml2pdf" not in content
        assert "flask>=3.0.0" in content
