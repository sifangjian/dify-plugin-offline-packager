"""
API 路由聚合模块

聚合所有 API 路由模块，统一注册到 FastAPI 应用：
- marketplace: Marketplace 相关 API
- pack: 打包相关 API
- sse: SSE 事件推送 API

同时提供健康检查接口。
"""

from fastapi import APIRouter

from app.api import marketplace, pack, sse

api_router = APIRouter()
api_router.include_router(marketplace.router)
api_router.include_router(pack.router)
api_router.include_router(sse.router)


@api_router.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    """
    健康检查接口

    用于负载均衡器和监控系统检测服务状态。

    Returns:
        dict: 包含状态信息的字典
    """
    return {"status": "ok"}
