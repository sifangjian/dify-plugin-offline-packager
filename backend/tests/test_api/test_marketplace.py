import httpx
import respx
from fastapi.testclient import TestClient

from app.main import app

MARKETPLACE_BASE_URL = "https://marketplace.dify.ai"
SEARCH_URL = f"{MARKETPLACE_BASE_URL}/api/v1/plugins/search/basic"


class TestSearchPluginsEndpoint:
    @respx.mock
    def test_search_with_keyword_returns_200(self):
        mock_response = {
            "code": 0,
            "data": {
                "plugins": [
                    {
                        "type": "plugin",
                        "name": "agent",
                        "org": "langgenius",
                        "plugin_id": "langgenius/agent",
                        "label": {"en_US": "Agent"},
                    }
                ],
                "total": 1,
            },
        }
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        with TestClient(app) as client:
            response = client.post("/api/v1/marketplace/search", json={"keyword": "agent"})

        assert response.status_code == 200
        body = response.json()
        assert "plugins" in body
        assert "total" in body
        assert body["total"] == 1
        assert body["plugins"][0]["name"] == "agent"

    @respx.mock
    def test_search_with_category_returns_200(self):
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

        with TestClient(app) as client:
            response = client.post("/api/v1/marketplace/search", json={"category": "model"})

        assert response.status_code == 200
        body = response.json()
        assert body["plugins"][0]["category"] == "model"

    @respx.mock
    def test_search_with_default_params_returns_200(self):
        mock_response = {
            "code": 0,
            "data": {"plugins": [], "total": 0},
        }
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        with TestClient(app) as client:
            response = client.post("/api/v1/marketplace/search", json={})

        assert response.status_code == 200
        body = response.json()
        assert body["plugins"] == []
        assert body["total"] == 0

    @respx.mock
    def test_search_marketplace_error_returns_503(self):
        respx.post(SEARCH_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/marketplace/search", json={"keyword": "agent"})

        assert response.status_code == 503
        body = response.json()
        assert body == {"error": {"code": "MARKETPLACE_API_ERROR", "message": "无法连接到 Marketplace API，请稍后重试"}}

    @respx.mock
    def test_search_5xx_returns_503(self):
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(500, json={"code": 1, "msg": "Internal Error"}))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/marketplace/search", json={"keyword": "agent"})

        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "MARKETPLACE_API_ERROR"
