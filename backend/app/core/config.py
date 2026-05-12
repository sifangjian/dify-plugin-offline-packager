from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MARKETPLACE_API_URL: str = "https://marketplace.dify.ai"
    PIP_MIRROR_URL: str = "https://mirrors.aliyun.com/pypi/simple"
    GITHUB_API_URL: str = "https://github.com"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    MAX_UPLOAD_SIZE_MB: int = 500
    WORK_DIR: str = "/app/workspace"
    DIFY_PLUGIN_CLI_PATH: str = "/app/dify-plugin-linux-amd64-5g"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    return Settings()
