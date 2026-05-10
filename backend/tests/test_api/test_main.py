from fastapi.testclient import TestClient

from app.core.exceptions import AppException, MarketplaceAPIError
from app.main import app


class TestHealthCheck:
    def test_health_check_returns_ok(self):
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestNotFoundRoute:
    def test_nonexistent_route_returns_404(self):
        client = TestClient(app)
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404


class TestLifespanIntegration:
    def test_app_has_lifespan(self):
        assert app.router.lifespan_context is not None

    def test_httpx_client_available_after_startup(self):
        with TestClient(app) as client:
            assert hasattr(client.app.state, "httpx_client")
            from httpx import AsyncClient

            assert isinstance(client.app.state.httpx_client, AsyncClient)


class TestExceptionHandlers:
    def test_app_exception_handler_registered(self):
        assert AppException in app.exception_handlers

    def test_unhandled_exception_handler_registered(self):
        assert Exception in app.exception_handlers

    def test_marketplace_api_error_returns_503(self):
        from fastapi import FastAPI

        test_app = FastAPI(lifespan=app.router.lifespan_context)
        test_app.include_router(app.router)
        from app.core.exceptions import app_exception_handler, unhandled_exception_handler

        test_app.add_exception_handler(AppException, app_exception_handler)
        test_app.add_exception_handler(Exception, unhandled_exception_handler)

        @test_app.get("/test-error")
        async def raise_marketplace_error():
            raise MarketplaceAPIError("测试错误")

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/test-error")
        assert response.status_code == 503
        assert response.json() == {"error": {"code": "MARKETPLACE_API_ERROR", "message": "测试错误"}}

    def test_generic_exception_returns_500(self):
        from fastapi import FastAPI

        test_app = FastAPI()
        from app.core.exceptions import unhandled_exception_handler

        test_app.add_exception_handler(Exception, unhandled_exception_handler)

        @test_app.get("/test-generic-error")
        async def raise_generic_error():
            raise RuntimeError("something broke")

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/test-generic-error")
        assert response.status_code == 500
        assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "服务内部错误，请稍后重试"}}


class TestRouterRegistration:
    def test_api_router_included(self):
        routes = [route.path for route in app.routes]
        assert "/api/v1/health" in routes
