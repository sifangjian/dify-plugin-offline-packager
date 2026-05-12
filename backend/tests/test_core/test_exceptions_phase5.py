from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppException,
    PackageError,
    StorageError,
    app_exception_handler,
)


class TestPackageError:
    def test_default_values(self):
        exc = PackageError("打包失败")
        assert exc.message == "打包失败"
        assert exc.code == "PACKAGE_ERROR"
        assert exc.status_code == 500

    def test_custom_code_and_status(self):
        exc = PackageError("未找到该打包任务", code="NOT_FOUND", status_code=404)
        assert exc.message == "未找到该打包任务"
        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404

    def test_inherits_app_exception(self):
        exc = PackageError("error")
        assert isinstance(exc, AppException)
        assert isinstance(exc, Exception)

    def test_default_message(self):
        exc = PackageError()
        assert exc.message == "打包过程失败"
        assert exc.code == "PACKAGE_ERROR"
        assert exc.status_code == 500


class TestStorageError:
    def test_default_values(self):
        exc = StorageError()
        assert exc.message == "文件存储操作失败"
        assert exc.code == "STORAGE_ERROR"
        assert exc.status_code == 500

    def test_custom_message(self):
        exc = StorageError("自定义存储错误")
        assert exc.message == "自定义存储错误"
        assert exc.code == "STORAGE_ERROR"

    def test_inherits_app_exception(self):
        exc = StorageError()
        assert isinstance(exc, AppException)


class TestPackageErrorInHandler:
    def test_package_error_returns_correct_json(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise PackageError("打包失败")

        app.add_exception_handler(AppException, app_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 500
        assert response.json() == {"error": {"code": "PACKAGE_ERROR", "message": "打包失败"}}

    def test_package_error_with_404(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise PackageError("未找到该打包任务", code="NOT_FOUND", status_code=404)

        app.add_exception_handler(AppException, app_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 404
        assert response.json() == {"error": {"code": "NOT_FOUND", "message": "未找到该打包任务"}}

    def test_storage_error_returns_correct_json(self):
        app = FastAPI()

        @app.get("/test")
        async def raise_error():
            raise StorageError()

        app.add_exception_handler(AppException, app_exception_handler)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 500
        assert response.json() == {"error": {"code": "STORAGE_ERROR", "message": "文件存储操作失败"}}
