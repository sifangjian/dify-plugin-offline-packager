"""
Marketplace 服务模块

提供与 Dify Marketplace API 交互的服务，包括：
- 插件搜索：按关键词和分类搜索插件
- 插件详情：获取指定插件的详细信息
- 插件下载：下载指定版本的插件包
- 插件集合：获取插件集合列表
- 批量查询：批量获取多个插件的信息

该服务作为 Marketplace API 的客户端，封装了 HTTP 请求和错误处理逻辑。
"""

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
    """
    Marketplace API 服务类

    封装与 Dify Marketplace 的所有交互逻辑，提供类型安全的 API 调用。

    Attributes:
        _client: httpx 异步客户端
        _base_url: Marketplace API 基础 URL
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str):
        """
        初始化 Marketplace 服务

        Args:
            client: httpx 异步客户端实例
            base_url: Marketplace API 基础 URL，如 https://marketplace.dify.ai
        """
        self._client = client
        self._base_url = base_url

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """
        发送 API 请求

        统一处理 HTTP 请求、响应解析和错误处理。

        Args:
            method: HTTP 方法（GET、POST 等）
            path: API 路径
            **kwargs: 传递给 httpx.request 的其他参数

        Returns:
            dict: API 响应的 data 字段内容

        Raises:
            MarketplaceAPIError: 请求失败或 API 返回错误时抛出
        """
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
        """
        搜索插件

        按关键词和分类搜索 Marketplace 中的插件。

        Args:
            keyword: 搜索关键词
            category: 插件分类
            page: 页码，从 1 开始
            page_size: 每页数量

        Returns:
            SearchResponse: 搜索结果，包含插件列表和总数
        """
        data = await self._request(
            "POST",
            "/api/v1/plugins/search/advanced",
            json={"query": keyword, "category": category, "page": page, "page_size": page_size},
        )
        plugins = [PluginInfo(**p) for p in data.get("plugins", [])]
        return SearchResponse(plugins=plugins, total=data.get("total", 0))

    async def get_plugin_detail(self, author: str, name: str, language: str | None = None) -> PluginInfo:
        """
        获取插件详情

        获取指定作者和名称的插件详细信息。

        Args:
            author: 插件作者标识
            name: 插件名称
            language: 请求的语言版本（如 zh_Hans），不传则返回默认语言

        Returns:
            PluginInfo: 插件详细信息
        """
        params = {}
        if language:
            params["language"] = language
        data = await self._request("GET", f"/api/v1/plugins/{author}/{name}", params=params)
        return PluginInfo(**data.get("plugin", {}))

    async def get_collections(self, page: int, page_size: int) -> CollectionsResponse:
        """
        获取插件集合列表

        获取 Marketplace 中的插件集合，集合是插件的分组展示方式。

        Args:
            page: 页码，从 1 开始
            page_size: 每页数量

        Returns:
            CollectionsResponse: 集合列表响应
        """
        data = await self._request("GET", "/api/v1/collections", params={"page": page, "page_size": page_size})
        collections = [CollectionInfo(**c) for c in data.get("collections", [])]
        return CollectionsResponse(collections=collections, total=data.get("total", 0))

    async def download_plugin(self, author: str, name: str, version: str) -> httpx.Response:
        """
        下载插件包

        从 Marketplace 下载指定版本的插件包（.difypkg 文件）。

        Args:
            author: 插件作者标识
            name: 插件名称
            version: 插件版本号

        Returns:
            httpx.Response: HTTP 响应对象，包含插件包二进制内容

        Raises:
            MarketplaceAPIError: 下载失败时抛出
        """
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
        """
        批量获取插件信息

        根据 plugin_id 列表批量获取多个插件的详细信息。

        Args:
            plugin_ids: 插件 ID 列表

        Returns:
            BatchResponse: 批量查询结果
        """
        data = await self._request("POST", "/api/v1/plugins/batch", json={"plugin_ids": plugin_ids})
        plugins = [PluginInfo(**p) for p in data.get("plugins", [])]
        return BatchResponse(plugins=plugins)
