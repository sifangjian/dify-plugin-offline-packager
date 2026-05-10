from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppException,
    MarketplaceAPIError,
    app_exception_handler,
    unhandled_exception_handler,
)


class TestAppException:
    def test_default_values(self):
        exc = AppException("something went wrong")
        assert exc.message == "something went wrong"
        assert exc.code == "INTERNAL_ERROR"
        assert exc.status_code == 500

    def test_custom_code_and_status(self):
        exc = AppException("not found", code="NOT_FOUND", status_code=404)
        assert exc.message == "not found"
        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404

    def test_is_exception(self):
        exc = AppException("error")
        assert isinstance(exc, Exception)


class TestMarketplaceAPIError:
    def test_default_values(self):
        exc = MarketplaceAPIError("测试错误")
        assert exc.message == "测试错误"
        assert exc.code == "MARKETPLACE_API_ERROR"
        assert exc.status_code == 503

    def test_custom_code_and_status(self):
        exc = MarketplaceAPIError("未找到", code="NOT_FOUND", status_code=404)
        assert exc.message == "未找到"
        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404

    def test_inherits_app_exception(self):
        exc = MarketplaceAPIError("error")
        assert isinstance(exc, AppException)
        assert isinstance(exc, Exception)

    def test_default_message(self):
        exc = MarketplaceAPIError()
        assert exc.message == "无法连接到 Marketplace API，请稍后重试"
        assert exc.code == "MARKETPLACE_API_ERROR"
        assert exc.status_code == 503


class TestAppExceptionHandler:
    def test_returns_correct_json_response(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise AppException("测试错误", code="TEST_ERROR", status_code=400)

        app.add_exception_handler(AppException, app_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        assert response.json() == {"error": {"code": "TEST_ERROR", "message": "测试错误"}}

    def test_marketplace_api_error_returns_503(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise MarketplaceAPIError("测试错误")

        app.add_exception_handler(AppException, app_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 503
        assert response.json() == {"error": {"code": "MARKETPLACE_API_ERROR", "message": "测试错误"}}

    def test_marketplace_api_error_with_404(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise MarketplaceAPIError("未找到", code="NOT_FOUND", status_code=404)

        app.add_exception_handler(AppException, app_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 404
        assert response.json() == {"error": {"code": "NOT_FOUND", "message": "未找到"}}

    def test_app_exception_with_500(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise AppException("内部错误")

        app.add_exception_handler(AppException, app_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 500
        assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "内部错误"}}


class TestUnhandledExceptionHandler:
    def test_returns_500_for_generic_exception(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise Exception("未知错误")

        app.add_exception_handler(Exception, unhandled_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 500
        assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "服务内部错误，请稍后重试"}}

    def test_does_not_expose_internal_error_details(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise RuntimeError("database connection string: postgres://admin:secret@db")

        app.add_exception_handler(Exception, unhandled_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert "database" not in body["error"]["message"]
        assert "secret" not in body["error"]["message"]
        assert body["error"]["message"] == "服务内部错误，请稍后重试"
