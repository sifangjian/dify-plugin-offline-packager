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
    settings = get_settings()
    client = request.app.state.httpx_client
    return MarketplaceService(client=client, base_url=settings.MARKETPLACE_API_URL)


_marketplace_service_dep = Depends(get_marketplace_service)


@router.post("/search", response_model=SearchResponse)
async def search_plugins(
    request: SearchRequest,
    service: MarketplaceService = _marketplace_service_dep,
) -> SearchResponse:
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
    return await service.get_collections(page=page, page_size=page_size)


@router.get("/{author}/{name}", response_model=PluginInfo)
async def get_plugin_detail(
    author: str, name: str, service: MarketplaceService = _marketplace_service_dep
) -> PluginInfo:
    return await service.get_plugin_detail(author, name)


@router.post("/batch", response_model=BatchResponse)
async def batch_get_plugins(
    request: BatchRequest,
    service: MarketplaceService = _marketplace_service_dep,
) -> BatchResponse:
    return await service.batch_get_plugins(request.plugin_ids)


@router.get("/{author}/{name}/{version}/download")
async def download_plugin(
    author: str, name: str, version: str, service: MarketplaceService = _marketplace_service_dep
) -> StreamingResponse:
    response = await service.download_plugin(author, name, version)

    async def _stream():
        yield response.content

    filename = f"{name}-{version}.difypkg"
    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
