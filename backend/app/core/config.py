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
- DEPENDENCY_VERSION_PATCHES: 依赖版本替换映射，用于处理 PyPI 上不存在的版本
- DEPENDENCY_REMOVAL_LIST: 需要移除的依赖包列表
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.plugin import Architecture

_CLI_DIR = str(Path(__file__).resolve().parent.parent)


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
        DEPENDENCY_VERSION_PATCHES: 依赖版本替换映射字典
        DEPENDENCY_REMOVAL_LIST: 需要移除的依赖包列表
    """

    MARKETPLACE_API_URL: str = "https://marketplace.dify.ai"
    PIP_MIRROR_URL: str = "https://mirrors.aliyun.com/pypi/simple"
    GITHUB_API_URL: str = "https://github.com"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    MAX_UPLOAD_SIZE_MB: int = 500
    UPLOAD_EXPIRE_HOURS: int = 24
    WORK_DIR: str = "/app/workspace"
    DIFY_PLUGIN_CLI_PATH: str = ""
    DIFY_PLUGIN_CLI_LINUX_AMD64: str = f"{_CLI_DIR}/dify-plugin-linux-amd64"
    DIFY_PLUGIN_CLI_LINUX_ARM64: str = f"{_CLI_DIR}/dify-plugin-linux-arm64"
    DIFY_PLUGIN_CLI_DARWIN_AMD64: str = f"{_CLI_DIR}/dify-plugin-darwin-amd64"
    DIFY_PLUGIN_CLI_DARWIN_ARM64: str = f"{_CLI_DIR}/dify-plugin-darwin-arm64"
    STATIC_DIR: str = "frontend/dist"
    # 依赖版本替换映射（暂时禁用）
    # 注意：这些预定义的版本替换规则可能不准确，需要根据实际情况调整
    # 当前策略：依赖动态版本同步（在下载依赖后根据实际下载的版本更新）
    DEPENDENCY_VERSION_PATCHES: dict[str, dict[str, str]] = {}
    
    # 需要移除的依赖包列表（已知不兼容或不需要的包）
    DEPENDENCY_REMOVAL_LIST: list[str] = ["xhtml2pdf", "svglib", "rlpycairo", "pycairo"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def get_cli_path(self, architecture: Architecture) -> str:
        mapping = {
            Architecture.LINUX_AMD64: self.DIFY_PLUGIN_CLI_LINUX_AMD64,
            Architecture.LINUX_ARM64: self.DIFY_PLUGIN_CLI_LINUX_ARM64,
            Architecture.DARWIN_AMD64: self.DIFY_PLUGIN_CLI_DARWIN_AMD64,
            Architecture.DARWIN_ARM64: self.DIFY_PLUGIN_CLI_DARWIN_ARM64,
        }
        return mapping[architecture]


def get_settings() -> Settings:
    """
    获取配置实例

    Returns:
        Settings: 配置实例
    """
    return Settings()
