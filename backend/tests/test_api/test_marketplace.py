import httpx
import respx
from fastapi.testclient import TestClient

from app.main import app

MARKETPLACE_BASE_URL = "https://marketplace.dify.ai"
SEARCH_URL = f"{MARKETPLACE_BASE_URL}/api/v1/plugins/search/advanced"
BATCH_URL = f"{MARKETPLACE_BASE_URL}/api/v1/plugins/batch"
DOWNLOAD_URL = f"{MARKETPLACE_BASE_URL}/api/v1/plugins/langgenius/agent/0.0.1/download"


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


class TestBatchGetPluginsEndpoint:
    @respx.mock
    def test_batch_with_plugin_ids_returns_200(self):
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
                    },
                    {
                        "type": "plugin",
                        "name": "chat",
                        "org": "langgenius",
                        "plugin_id": "langgenius/chat",
                        "label": {"en_US": "Chat"},
                    },
                ]
            },
        }
        respx.post(BATCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/marketplace/batch",
                json={"plugin_ids": ["langgenius/agent", "langgenius/chat"]},
            )

        assert response.status_code == 200
        body = response.json()
        assert "plugins" in body
        assert len(body["plugins"]) == 2
        assert body["plugins"][0]["name"] == "agent"
        assert body["plugins"][1]["name"] == "chat"

    @respx.mock
    def test_batch_with_empty_ids_returns_empty_list(self):
        mock_response = {"code": 0, "data": {"plugins": []}}
        respx.post(BATCH_URL).mock(return_value=httpx.Response(200, json=mock_response))

        with TestClient(app) as client:
            response = client.post("/api/v1/marketplace/batch", json={"plugin_ids": []})

        assert response.status_code == 200
        body = response.json()
        assert body["plugins"] == []

    @respx.mock
    def test_batch_marketplace_error_returns_503(self):
        respx.post(BATCH_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/marketplace/batch",
                json={"plugin_ids": ["langgenius/agent"]},
            )

        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "MARKETPLACE_API_ERROR"


class TestDownloadPluginEndpoint:
    @respx.mock
    def test_download_returns_200_with_binary_content(self):
        binary_content = b"fake-plugin-package-content"
        respx.get(DOWNLOAD_URL).mock(return_value=httpx.Response(200, content=binary_content))

        with TestClient(app) as client:
            response = client.get("/api/v1/marketplace/langgenius/agent/0.0.1/download")

        assert response.status_code == 200
        assert response.content == binary_content

    @respx.mock
    def test_download_returns_correct_content_disposition_header(self):
        binary_content = b"fake-plugin-package-content"
        respx.get(DOWNLOAD_URL).mock(return_value=httpx.Response(200, content=binary_content))

        with TestClient(app) as client:
            response = client.get("/api/v1/marketplace/langgenius/agent/0.0.1/download")

        assert response.status_code == 200
        assert response.headers["content-disposition"] == 'attachment; filename="agent-0.0.1.difypkg"'

    @respx.mock
    def test_download_returns_octet_stream_content_type(self):
        binary_content = b"fake-plugin-package-content"
        respx.get(DOWNLOAD_URL).mock(return_value=httpx.Response(200, content=binary_content))

        with TestClient(app) as client:
            response = client.get("/api/v1/marketplace/langgenius/agent/0.0.1/download")

        assert response.status_code == 200
        assert "application/octet-stream" in response.headers["content-type"]

    @respx.mock
    def test_download_not_found_returns_404(self):
        respx.get(DOWNLOAD_URL).mock(return_value=httpx.Response(404, json={"code": 1, "msg": "not found"}))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/marketplace/langgenius/agent/0.0.1/download")

        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert "未找到该插件" in body["error"]["message"]
