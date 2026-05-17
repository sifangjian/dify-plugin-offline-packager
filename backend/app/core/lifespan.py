"""
应用生命周期管理模块

管理 FastAPI 应用的启动和关闭生命周期：
- 启动时：初始化 HTTP 客户端、存储服务、打包服务
- 关闭时：清理资源、关闭 HTTP 客户端

使用 FastAPI 的 lifespan 上下文管理器实现。
"""

import contextlib
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.packager import PackagerService
from app.services.storage import StorageService


@contextlib.asynccontextmanager
async def lifespan(app):
    """
    应用生命周期上下文管理器

    管理应用启动和关闭时的资源初始化和清理。

    启动时：
    1. 创建 httpx 异步客户端
    2. 初始化存储服务
    3. 创建并启动打包服务
    4. 将服务实例保存到应用状态

    关闭时：
    1. 停止打包服务
    2. 关闭 httpx 客户端

    Args:
        app: FastAPI 应用实例

    Yields:
        None: 控制权交还给应用
    """
    settings = get_settings()

    httpx_client = httpx.AsyncClient(timeout=30.0)

    work_dir = Path(settings.WORK_DIR)
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        work_dir = Path("./workspace")
        work_dir.mkdir(parents=True, exist_ok=True)
    storage = StorageService(work_dir=work_dir)

    packager = PackagerService(
        httpx_client=httpx_client,
        settings=settings,
        storage=storage,
    )
    packager.start()

    app.state.packager_service = packager
    app.state.httpx_client = httpx_client

    yield

    await packager.stop()
    await httpx_client.aclose()
