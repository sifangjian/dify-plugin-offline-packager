import os
from unittest.mock import patch

from app.core.config import Settings, get_settings


class TestSettings:
    def test_default_values(self):
        settings = Settings()
        assert settings.MARKETPLACE_API_URL == "https://marketplace.dify.ai"
        assert settings.PIP_MIRROR_URL == "https://mirrors.aliyun.com/pypi/simple"
        assert settings.GITHUB_API_URL == "https://github.com"
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8080
        assert settings.MAX_UPLOAD_SIZE_MB == 500
        assert settings.WORK_DIR == "/app/workspace"

    def test_env_override_marketplace_api_url(self):
        with patch.dict(os.environ, {"MARKETPLACE_API_URL": "https://custom.api"}):
            settings = Settings()
            assert settings.MARKETPLACE_API_URL == "https://custom.api"

    def test_env_override_port(self):
        with patch.dict(os.environ, {"PORT": "9000"}):
            settings = Settings()
            assert settings.PORT == 9000

    def test_env_override_host(self):
        with patch.dict(os.environ, {"HOST": "127.0.0.1"}):
            settings = Settings()
            assert settings.HOST == "127.0.0.1"

    def test_env_override_work_dir(self):
        with patch.dict(os.environ, {"WORK_DIR": "/tmp/workspace"}):
            settings = Settings()
            assert settings.WORK_DIR == "/tmp/workspace"

    def test_env_override_max_upload_size(self):
        with patch.dict(os.environ, {"MAX_UPLOAD_SIZE_MB": "1000"}):
            settings = Settings()
            assert settings.MAX_UPLOAD_SIZE_MB == 1000

    def test_env_override_pip_mirror_url(self):
        with patch.dict(os.environ, {"PIP_MIRROR_URL": "https://pypi.org/simple"}):
            settings = Settings()
            assert settings.PIP_MIRROR_URL == "https://pypi.org/simple"

    def test_env_override_github_api_url(self):
        with patch.dict(os.environ, {"GITHUB_API_URL": "https://github.enterprise.com"}):
            settings = Settings()
            assert settings.GITHUB_API_URL == "https://github.enterprise.com"


class TestGetSettings:
    def test_get_settings_returns_settings_instance(self):
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_returns_default_values(self):
        settings = get_settings()
        assert settings.MARKETPLACE_API_URL == "https://marketplace.dify.ai"
        assert settings.PORT == 8080

    def test_get_settings_with_env_override(self):
        with patch.dict(os.environ, {"MARKETPLACE_API_URL": "https://custom.api"}):
            settings = get_settings()
            assert settings.MARKETPLACE_API_URL == "https://custom.api"


class TestSettingsDotEnvFile:
    def test_dotenv_file_override(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=9000\n", encoding="utf-8")
        settings = Settings(_env_file=str(env_file))
        assert settings.PORT == 9000

    def test_dotenv_file_multiple_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=9000\nMARKETPLACE_API_URL=https://custom.api\n", encoding="utf-8")
        settings = Settings(_env_file=str(env_file))
        assert settings.PORT == 9000
        assert settings.MARKETPLACE_API_URL == "https://custom.api"

    def test_env_overrides_dotenv(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=9000\n", encoding="utf-8")
        with patch.dict(os.environ, {"PORT": "7000"}):
            settings = Settings(_env_file=str(env_file))
            assert settings.PORT == 7000
