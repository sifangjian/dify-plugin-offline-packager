"""
应用配置模块

使用 pydantic-settings 管理应用配置，支持从环境变量和 .env 文件加载配置。

配置项：
- MARKETPLACE_API_URL: Dify Marketplace API 地址
- PIP_MIRROR_URL: PyPI 镜像源地址，用于加速依赖下载
- GITHUB_API_URL: GitHub API 地址
- HOST: 服务监听地址
- PORT: 服务监听端口
- MAX_UPLOAD_SIZE_MB: 最大上传文件大小（MB）
- WORK_DIR: 工作目录，用于存储临时文件和打包结果
- DIFY_PLUGIN_CLI_PATH: Dify Plugin CLI 工具路径
- STATIC_DIR: 前端静态文件目录
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类

    定义所有可配置项及其默认值。
    支持从环境变量和 .env 文件加载配置。

    Attributes:
        MARKETPLACE_API_URL: Marketplace API 基础 URL
        PIP_MIRROR_URL: PyPI 镜像源 URL
        GITHUB_API_URL: GitHub API URL
        HOST: 服务监听地址
        PORT: 服务监听端口
        MAX_UPLOAD_SIZE_MB: 最大上传文件大小
        WORK_DIR: 工作目录路径
        DIFY_PLUGIN_CLI_PATH: Dify Plugin CLI 可执行文件路径
        STATIC_DIR: 前端静态文件目录
    """

    MARKETPLACE_API_URL: str = "https://marketplace.dify.ai"
    PIP_MIRROR_URL: str = "https://mirrors.aliyun.com/pypi/simple"
    GITHUB_API_URL: str = "https://github.com"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    MAX_UPLOAD_SIZE_MB: int = 500
    WORK_DIR: str = "/app/workspace"
    DIFY_PLUGIN_CLI_PATH: str = "/app/dify-plugin-linux-amd64-5g"
    STATIC_DIR: str = "frontend/dist"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    """
    获取配置实例

    Returns:
        Settings: 配置实例
    """
    return Settings()
