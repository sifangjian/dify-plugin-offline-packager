import httpx

from app.core.exceptions import MarketplaceAPIError
from app.models.marketplace import (
    BatchResponse,
    CollectionInfo,
    CollectionsResponse,
    PluginInfo,
    SearchResponse,
)


class MarketplaceService:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self._client = client
        self._base_url = base_url

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = await self._client.request(method, f"{self._base_url}{path}", **kwargs)
            response.raise_for_status()
            body = response.json()
            if body.get("code") != 0:
                raise MarketplaceAPIError(body.get("msg", "Marketplace API 返回错误")) from None
            return body.get("data", {})
        except httpx.TimeoutException:
            raise MarketplaceAPIError("无法连接到 Marketplace API，请稍后重试") from None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MarketplaceAPIError("未找到该插件", code="NOT_FOUND", status_code=404) from None
            raise MarketplaceAPIError("无法连接到 Marketplace API，请稍后重试") from None

    async def search_plugins(self, keyword: str, category: str, page: int, page_size: int) -> SearchResponse:
        data = await self._request(
            "POST",
            "/api/v1/plugins/search/advanced",
            json={"query": keyword, "category": category, "page": page, "page_size": page_size},
        )
        plugins = [PluginInfo(**p) for p in data.get("plugins", [])]
        return SearchResponse(plugins=plugins, total=data.get("total", 0))

    async def get_plugin_detail(self, author: str, name: str) -> PluginInfo:
        data = await self._request("GET", f"/api/v1/plugins/{author}/{name}")
        return PluginInfo(**data.get("plugin", {}))

    async def get_collections(self, page: int, page_size: int) -> CollectionsResponse:
        data = await self._request("GET", "/api/v1/collections", params={"page": page, "page_size": page_size})
        collections = [CollectionInfo(**c) for c in data.get("collections", [])]
        return CollectionsResponse(collections=collections, total=data.get("total", 0))

    async def download_plugin(self, author: str, name: str, version: str) -> httpx.Response:
        try:
            response = await self._client.request(
                "GET",
                f"{self._base_url}/api/v1/plugins/{author}/{name}/{version}/download",
            )
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise MarketplaceAPIError("无法连接到 Marketplace API，请稍后重试") from None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MarketplaceAPIError("未找到该插件", code="NOT_FOUND", status_code=404) from None
            raise MarketplaceAPIError("无法连接到 Marketplace API，请稍后重试") from None

    async def batch_get_plugins(self, plugin_ids: list[str]) -> BatchResponse:
        data = await self._request("POST", "/api/v1/plugins/batch", json={"plugin_ids": plugin_ids})
        plugins = [PluginInfo(**p) for p in data.get("plugins", [])]
        return BatchResponse(plugins=plugins)
