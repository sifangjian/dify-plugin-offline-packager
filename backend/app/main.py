"""
FastAPI 应用入口模块

创建并配置 FastAPI 应用实例：
- 注册 API 路由
- 配置异常处理器
- 挂载静态文件服务
- 配置 SPA 路由回退
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.lifespan import lifespan

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

app = FastAPI(
    title="Dify Plugin Offline Packager",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_router)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

_settings = get_settings()
_static_dir = Path(_settings.STATIC_DIR)
if not _static_dir.is_absolute():
    _static_dir = _PROJECT_ROOT / _static_dir

if _static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="static-assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str) -> FileResponse:
        """
        SPA 路由回退处理

        对于所有未匹配的路由，返回前端 index.html，
        支持前端路由（如 Vue Router 的 history 模式）。

        Args:
            path: 请求路径

        Returns:
            FileResponse: 静态文件响应
        """
        file_path = _static_dir / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_static_dir / "index.html")
