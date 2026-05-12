import os
from unittest.mock import patch

from app.core.config import Settings


class TestDifyPluginCliPath:
    def test_default_value(self):
        settings = Settings()
        assert settings.DIFY_PLUGIN_CLI_PATH == "/app/dify-plugin-linux-amd64-5g"

    def test_env_override(self):
        with patch.dict(os.environ, {"DIFY_PLUGIN_CLI_PATH": "/usr/local/bin/dify-plugin"}):
            settings = Settings()
            assert settings.DIFY_PLUGIN_CLI_PATH == "/usr/local/bin/dify-plugin"
