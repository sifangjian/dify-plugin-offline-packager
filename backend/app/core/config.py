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
    DEPENDENCY_VERSION_PATCHES: dict[str, dict[str, str]] = {
        "greenlet": {
            "==3.3.0": "greenlet>=3.2.0",
            "==3.3.1": "greenlet>=3.2.0",
            "~=3.3.0": "greenlet~=3.2.0",
            "~=3.3.1": "greenlet~=3.2.0",
        },
        "contourpy": {
            "==1.3.3": "contourpy>=1.3.0",
            "==1.3.4": "contourpy>=1.3.0",
            "~=1.3.3": "contourpy~=1.3.0",
            "~=1.3.4": "contourpy~=1.3.0",
        },
        "pandas": {
            "~=3.0.1": "pandas>=2.2.0",
            "~=3.0.0": "pandas>=2.2.0",
            "==3.0.1": "pandas>=2.2.0",
            "==3.0.0": "pandas>=2.2.0",
        },
        "numpy": {
            "==2.3.0": "numpy>=2.2.0",
            "==2.3.1": "numpy>=2.2.0",
            "==2.3.5": "numpy>=2.2.0",
            "==2.3.4": "numpy>=2.2.0",
            "==2.3.3": "numpy>=2.2.0",
            "==2.3.2": "numpy>=2.2.0",
            "~=2.3.5": "numpy~=2.2.0",
            "~=2.3.4": "numpy~=2.2.0",
            "~=2.3.3": "numpy~=2.2.0",
            "~=2.3.2": "numpy~=2.2.0",
            "~=2.3.1": "numpy~=2.2.0",
            "~=2.3.0": "numpy~=2.2.0",
        },
        "pydantic_core": {
            "==2.33.2": "pydantic_core>=2.30.0",
            "==2.33.1": "pydantic_core>=2.30.0",
            "==2.46.4": "pydantic_core>=2.40.0",
            "~=2.33.2": "pydantic_core~=2.30.0",
            "~=2.33.1": "pydantic_core~=2.30.0",
            "~=2.46.4": "pydantic_core~=2.40.0",
        },
        "pydantic": {
            "==2.11.3": "pydantic>=2.8.0",
            "==2.11.2": "pydantic>=2.8.0",
            "==2.11.1": "pydantic>=2.8.0",
            "==2.11.0": "pydantic>=2.8.0",
            "~=2.11.3": "pydantic~=2.8.0",
            "~=2.11.2": "pydantic~=2.8.0",
            "~=2.11.1": "pydantic~=2.8.0",
            "~=2.11.0": "pydantic~=2.8.0",
        },
        "pydantic-settings": {
            "==2.14.1": "pydantic-settings>=2.13.0",
            "==2.14.0": "pydantic-settings>=2.13.0",
            "~=2.14.1": "pydantic-settings~=2.13.0",
            "~=2.14.0": "pydantic-settings~=2.13.0",
        },
        "fonttools": {
            "==4.61.1": "fonttools>=4.50.0",
            "~=4.61.1": "fonttools~=4.50.0",
        },
        "matplotlib": {
            "==3.10.3": "matplotlib>=3.9.0",
            "==3.10.2": "matplotlib>=3.9.0",
            "==3.10.1": "matplotlib>=3.9.0",
            "==3.10.0": "matplotlib>=3.9.0",
            "~=3.10.3": "matplotlib~=3.9.0",
            "~=3.10.2": "matplotlib~=3.9.0",
            "~=3.10.1": "matplotlib~=3.9.0",
            "~=3.10.0": "matplotlib~=3.9.0",
        },
        "regex": {
            "==2025.11.3": "regex>=2025.1.0",
            "==2026.5.9": "regex>=2025.1.0",
            "~=2025.11.3": "regex~=2025.1.0",
            "~=2026.5.9": "regex~=2025.1.0",
        },
        "certifi": {
            "==2025.11.12": "certifi>=2025.1.0",
            "~=2025.11.12": "certifi~=2025.1.0",
        },
        "charset-normalizer": {
            "==3.4.4": "charset-normalizer>=3.4.0",
            "==3.4.7": "charset-normalizer>=3.4.0",
            "~=3.4.4": "charset-normalizer~=3.4.0",
        },
        "urllib3": {
            "==2.6.2": "urllib3>=2.5.0",
            "~=2.6.2": "urllib3~=2.5.0",
        },
        "werkzeug": {
            "==3.1.7": "werkzeug>=3.0.0",
            "~=3.1.7": "werkzeug~=3.0.0",
        },
        "yarl": {
            "==1.9.11": "yarl>=1.9.0",
            "~=1.9.11": "yarl~=1.9.0",
        },
        "multidict": {
            "==6.7.0": "multidict>=6.6.0",
            "==6.7.1": "multidict>=6.6.0",
            "~=6.7.0": "multidict~=6.6.0",
            "~=6.7.1": "multidict~=6.6.0",
        },
        "packaging": {
            "==26.0": "packaging>=24.0.0",
            "~=26.0": "packaging~=24.0",
        },
        "zope-interface": {
            "==8.4": "zope-interface>=8.0",
            "==8.1.1": "zope-interface>=8.0",
            "~=8.4": "zope-interface~=8.0",
            "~=8.1.1": "zope-interface~=8.0",
        },
        "anyio": {
            "==4.12.0": "anyio>=4.10.0",
            "==4.13.0": "anyio>=4.10.0",
            "~=4.12.0": "anyio~=4.10.0",
            "~=4.13.0": "anyio~=4.10.0",
        },
        "gevent": {
            "==25.5.1": "gevent>=24.11.0",
            "~=25.5.1": "gevent~=24.11.0",
        },
        "dpkt": {
            "==1.9.8": "dpkt>=1.9.6",
            "~=1.9.8": "dpkt~=1.9.6",
        },
        "typing-inspection": {
            "==0.4.2": "typing-inspection>=0.4.0",
            "~=0.4.2": "typing-inspection~=0.4.0",
        },
        "python-dotenv": {
            "==1.2.1": "python-dotenv>=1.2.0",
            "==1.2.2": "python-dotenv>=1.2.0",
            "~=1.2.1": "python-dotenv~=1.2.0",
            "~=1.2.2": "python-dotenv~=1.2.0",
        },
        "requests": {
            "==2.32.5": "requests>=2.32.0",
            "~=2.32.5": "requests~=2.32.0",
        },
        "pyyaml": {
            "==6.0.3": "pyyaml>=6.0.0",
            "~=6.0.3": "pyyaml~=6.0.0",
        },
        "typing-extensions": {
            "==4.15.0": "typing-extensions>=4.12.0",
            "~=4.15.0": "typing-extensions~=4.12.0",
        },
        "click": {
            "==8.3.1": "click>=8.1.0",
            "==8.3.3": "click>=8.1.0",
            "~=8.3.1": "click~=8.1.0",
            "~=8.3.3": "click~=8.1.0",
        },
        "blinker": {
            "==1.9.0": "blinker>=1.7.0",
            "~=1.9.0": "blinker~=1.7.0",
        },
        "annotated-types": {
            "==0.7.0": "annotated-types>=0.6.0",
            "~=0.7.0": "annotated-types~=0.6.0",
        },
        "h11": {
            "==0.16.0": "h11>=0.14.0",
            "~=0.16.0": "h11~=0.14.0",
        },
        "httpcore": {
            "==1.0.9": "httpcore>=1.0.0",
            "~=1.0.9": "httpcore~=1.0.0",
        },
        "httpx": {
            "==0.28.1": "httpx>=0.27.0",
            "~=0.28.1": "httpx~=0.27.0",
        },
        "idna": {
            "==3.11": "idna>=3.6",
            "==3.14": "idna>=3.6",
            "~=3.11": "idna~=3.6",
            "~=3.14": "idna~=3.6",
        },
        "itsdangerous": {
            "==2.2.0": "itsdangerous>=2.1.0",
            "~=2.2.0": "itsdangerous~=2.1.0",
        },
        "jinja2": {
            "==3.1.6": "jinja2>=3.1.0",
            "~=3.1.6": "jinja2~=3.1.0",
        },
        "markupsafe": {
            "==3.0.3": "markupsafe>=3.0.0",
            "~=3.0.3": "markupsafe~=3.0.0",
        },
        "kiwisolver": {
            "==1.4.9": "kiwisolver>=1.4.0",
            "~=1.4.9": "kiwisolver~=1.4.0",
        },
        "cycler": {
            "==0.12.1": "cycler>=0.12.0",
            "~=0.12.1": "cycler~=0.12.0",
        },
        "socksio": {
            "==1.0.0": "socksio>=1.0.0",
            "~=1.0.0": "socksio>=1.0.0",
        },
        "tiktoken": {
            "==0.8.0": "tiktoken>=0.7.0",
            "~=0.8.0": "tiktoken~=0.7.0",
        },
        "zope-event": {
            "==6.1": "zope-event>=6.0",
            "==6.2": "zope-event>=6.0",
            "~=6.1": "zope-event~=6.0",
            "~=6.2": "zope-event~=6.0",
        },
        "flask": {
            "==3.0.3": "flask>=3.0.0",
            "~=3.0.3": "flask~=3.0.0",
        },
        "dify-plugin": {
            "==0.7.4": "dify-plugin>=0.7.0",
            "==0.2.1": "dify-plugin>=0.2.0",
        },
        "pandas[output_formatting]": {
            "~=3.0.1": "pandas>=2.2.0",
            "~=3.0.0": "pandas>=2.2.0",
        },
        "pymupdf": {
            "~=1.26.7": "PyMuPDF~=1.25.0",
            "~=1.26.5": "PyMuPDF~=1.25.0",
            "~=1.26.4": "PyMuPDF~=1.25.0",
            "~=1.26.3": "PyMuPDF~=1.25.0",
            "~=1.26.2": "PyMuPDF~=1.25.0",
            "~=1.26.1": "PyMuPDF~=1.25.0",
        },
        "pillow": {
            "~=12.1.0": "pillow~=12.0.0",
        },
        "pypandoc-binary": {
            "~=1.16.2": "pypandoc-binary~=1.14.0",
        },
        "xhtml2pdf": {
            "~=0.2.17": "xhtml2pdf~=0.2.16",
        },
        "markdown": {
            "~=3.10.2": "markdown~=3.8.0",
            "~=3.10.1": "markdown~=3.8.0",
        },
        "dify_plugin": {
            "~=0.7.1": "dify_plugin~=0.7.0",
            "~=0.2.1": "dify_plugin~=0.2.0",
        },
    }
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
