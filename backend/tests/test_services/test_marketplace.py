import json

import httpx
import pytest
import respx

from app.core.exceptions import MarketplaceAPIError
from app.models.marketplace import SearchResponse
from app.services.marketplace import MarketplaceService

BASE_URL = "https://marketplace.dify.ai"
SEARCH_URL = f"{BASE_URL}/api/v1/plugins/search/basic"


@pytest.fixture
def service():
    client = httpx.AsyncClient(timeout=10.0)
    return MarketplaceService(client=client, base_url=BASE_URL)


class TestSearchPlugins:
    @respx.mock
    async def test_search_returns_search_response(self, service):
        mock_response = {
            "code": 0,
            "data": {
                "plugins": [
                    {
                        "type": "plugin",
                        "name": "agent",
                        "org": "langgenius",
                        "plugin_id": "langgenius/agent",
                        "label": {"en_US": "Agent", "zh_Hans": "智能体"},
                        "install_count": 1000,
                    }
                ],
                "total": 1,
            },
        }
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        result = await service.search_plugins(keyword="agent", category="", page=1, page_size=20)

        assert isinstance(result, SearchResponse)
        assert result.total == 1
        assert len(result.plugins) == 1
        assert result.plugins[0].name == "agent"
        assert result.plugins[0].label.en_US == "Agent"

    @respx.mock
    async def test_search_empty_results(self, service):
        mock_response = {
            "code": 0,
            "data": {"plugins": [], "total": 0},
        }
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        result = await service.search_plugins(keyword="nonexistent", category="", page=1, page_size=20)

        assert isinstance(result, SearchResponse)
        assert result.total == 0
        assert result.plugins == []

    @respx.mock
    async def test_search_with_category(self, service):
        mock_response = {
            "code": 0,
            "data": {
                "plugins": [
                    {
                        "type": "plugin",
                        "name": "chat-model",
                        "org": "langgenius",
                        "plugin_id": "langgenius/chat-model",
                        "category": "model",
                    }
                ],
                "total": 1,
            },
        }
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        result = await service.search_plugins(keyword="", category="model", page=1, page_size=20)

        assert result.plugins[0].category == "model"

    @respx.mock
    async def test_search_sends_correct_request_body(self, service):
        route = respx.post(SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"plugins": [], "total": 0}})
        )

        await service.search_plugins(keyword="test", category="agent", page=2, page_size=10)

        assert route.called
        request = route.calls.last.request
        body = json.loads(request.content)
        assert body["keyword"] == "test"
        assert body["category"] == "agent"
        assert body["page"] == 2
        assert body["page_size"] == 10

    @respx.mock
    async def test_search_timeout_raises_marketplace_api_error(self, service):
        respx.post(SEARCH_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))

        with pytest.raises(MarketplaceAPIError) as exc_info:
            await service.search_plugins(keyword="agent", category="", page=1, page_size=20)

        assert "无法连接到 Marketplace API" in exc_info.value.message

    @respx.mock
    async def test_search_5xx_raises_marketplace_api_error(self, service):
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(500, json={"code": 1, "msg": "Internal Error"}))

        with pytest.raises(MarketplaceAPIError) as exc_info:
            await service.search_plugins(keyword="agent", category="", page=1, page_size=20)

        assert "无法连接到 Marketplace API" in exc_info.value.message
        assert exc_info.value.status_code == 503

    @respx.mock
    async def test_search_api_returns_error_code(self, service):
        mock_response = {"code": 1, "msg": "参数错误"}
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        with pytest.raises(MarketplaceAPIError) as exc_info:
            await service.search_plugins(keyword="agent", category="", page=1, page_size=20)

        assert exc_info.value.message == "参数错误"

    @respx.mock
    async def test_search_api_returns_error_code_without_msg(self, service):
        mock_response = {"code": 1}
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        with pytest.raises(MarketplaceAPIError) as exc_info:
            await service.search_plugins(keyword="agent", category="", page=1, page_size=20)

        assert "Marketplace API 返回错误" in exc_info.value.message
