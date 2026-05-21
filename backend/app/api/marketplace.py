"""
Marketplace API 接口模块

提供与 Dify Marketplace 交互的 RESTful API 接口：
- POST /api/v1/marketplace/search: 搜索插件
- GET /api/v1/marketplace/collections: 获取插件集合
- GET /api/v1/marketplace/{author}/{name}: 获取插件详情
- POST /api/v1/marketplace/batch: 批量获取插件信息
- GET /api/v1/marketplace/{author}/{name}/{version}/download: 下载插件包

这些接口作为 Marketplace API 的代理，转发前端请求到 Dify Marketplace。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.models.marketplace import (
    BatchRequest,
    BatchResponse,
    CollectionsResponse,
    PluginInfo,
    SearchRequest,
    SearchResponse,
)
from app.services.marketplace import MarketplaceService

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


def get_marketplace_service(request: Request) -> MarketplaceService:
    """
    获取 Marketplace 服务实例

    创建并返回 Marketplace 服务实例，使用应用级别的 httpx 客户端。

    Args:
        request: FastAPI 请求对象

    Returns:
        MarketplaceService: Marketplace 服务实例
    """
    settings = get_settings()
    client = request.app.state.httpx_client
    return MarketplaceService(client=client, base_url=settings.MARKETPLACE_API_URL)


_marketplace_service_dep = Depends(get_marketplace_service)


@router.post("/search", response_model=SearchResponse)
async def search_plugins(
    request: SearchRequest,
    service: MarketplaceService = _marketplace_service_dep,
) -> SearchResponse:
    """
    搜索插件

    按关键词和分类搜索 Marketplace 中的插件。

    Args:
        request: 搜索请求参数
        service: Marketplace 服务实例（依赖注入）

    Returns:
        SearchResponse: 搜索结果
    """
    return await service.search_plugins(
        keyword=request.keyword,
        category=request.category,
        page=request.page,
        page_size=request.page_size,
    )


@router.get("/collections", response_model=CollectionsResponse)
async def get_collections(
    page: int = 1,
    page_size: int = 20,
    service: MarketplaceService = _marketplace_service_dep,
) -> CollectionsResponse:
    """
    获取插件集合列表

    获取 Marketplace 中的插件集合（专题）列表。

    Args:
        page: 页码，默认为 1
        page_size: 每页数量，默认为 20
        service: Marketplace 服务实例（依赖注入）

    Returns:
        CollectionsResponse: 集合列表响应
    """
    return await service.get_collections(page=page, page_size=page_size)


@router.get("/{author}/{name}", response_model=PluginInfo)
async def get_plugin_detail(
    author: str, name: str, language: str | None = None, service: MarketplaceService = _marketplace_service_dep
) -> PluginInfo:
    """
    获取插件详情

    获取指定作者和名称的插件详细信息。

    Args:
        author: 插件作者标识
        name: 插件名称
        language: 请求的语言版本（如 zh_Hans），不传则返回默认语言
        service: Marketplace 服务实例（依赖注入）

    Returns:
        PluginInfo: 插件详细信息
    """
    return await service.get_plugin_detail(author, name, language=language)


@router.post("/batch", response_model=BatchResponse)
async def batch_get_plugins(
    request: BatchRequest,
    service: MarketplaceService = _marketplace_service_dep,
) -> BatchResponse:
    """
    批量获取插件信息

    根据 plugin_id 列表批量获取多个插件的详细信息。

    Args:
        request: 批量请求，包含 plugin_id 列表
        service: Marketplace 服务实例（依赖注入）

    Returns:
        BatchResponse: 批量查询结果
    """
    return await service.batch_get_plugins(request.plugin_ids)


@router.get("/{author}/{name}/{version}/download")
async def download_plugin(
    author: str, name: str, version: str, service: MarketplaceService = _marketplace_service_dep
) -> StreamingResponse:
    """
    下载插件包

    从 Marketplace 下载指定版本的插件包。

    Args:
        author: 插件作者标识
        name: 插件名称
        version: 插件版本号
        service: Marketplace 服务实例（依赖注入）

    Returns:
        StreamingResponse: 插件包文件流
    """
    response = await service.download_plugin(author, name, version)

    async def _stream():
        """
        文件流生成器

        将下载的内容作为流返回。
        """
        yield response.content

    filename = f"{name}-{version}.difypkg"
    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
