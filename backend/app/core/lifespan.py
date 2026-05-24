"""
应用生命周期管理模块

管理 FastAPI 应用的启动和关闭生命周期：
- 启动时：初始化 HTTP 客户端、存储服务、打包服务、过期清理任务
- 关闭时：清理资源、关闭 HTTP 客户端

使用 FastAPI 的 lifespan 上下文管理器实现。
"""

import asyncio
import contextlib
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.packager import PackagerService
from app.services.storage import StorageService


async def _cleanup_expired_uploads(storage: StorageService, interval_seconds: int) -> None:
    """定时清理过期的上传文件"""
    while True:
        await asyncio.sleep(interval_seconds)
        with contextlib.suppress(Exception):
            await storage.cleanup_expired_uploads()


@contextlib.asynccontextmanager
async def lifespan(app):
    """
    应用生命周期上下文管理器

    管理应用启动和关闭时的资源初始化和清理。

    启动时：
    1. 创建 httpx 异步客户端
    2. 初始化存储服务
    3. 创建并启动打包服务
    4. 启动过期文件清理定时任务
    5. 将服务实例保存到应用状态

    关闭时：
    1. 停止过期清理任务
    2. 停止打包服务
    3. 关闭 httpx 客户端

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
    storage = StorageService(work_dir=work_dir, upload_expire_hours=settings.UPLOAD_EXPIRE_HOURS)

    packager = PackagerService(
        httpx_client=httpx_client,
        settings=settings,
        storage=storage,
    )
    packager.start()

    cleanup_task = asyncio.create_task(_cleanup_expired_uploads(storage, 3600))

    app.state.packager_service = packager
    app.state.storage_service = storage
    app.state.settings = settings
    app.state.httpx_client = httpx_client

    yield

    cleanup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await cleanup_task

    await packager.stop()
    await httpx_client.aclose()
