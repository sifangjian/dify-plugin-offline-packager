import os
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import api_router
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.lifespan import lifespan


def _create_app_with_static_dir(static_dir: str) -> FastAPI:
    with patch.dict(os.environ, {"STATIC_DIR": static_dir}):
        from app.core.config import Settings

        settings = Settings()
        static_path = Path(settings.STATIC_DIR)

        test_app = FastAPI(lifespan=lifespan)
        test_app.include_router(api_router)
        test_app.add_exception_handler(AppException, app_exception_handler)
        test_app.add_exception_handler(Exception, unhandled_exception_handler)

        if static_path.is_dir():
            from fastapi.responses import FileResponse
            from fastapi.staticfiles import StaticFiles

            test_app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="static-assets")

            @test_app.get("/{path:path}")
            async def serve_spa(path: str) -> FileResponse:
                file_path = static_path / path
                if file_path.is_file():
                    return FileResponse(file_path)
                return FileResponse(static_path / "index.html")

        return test_app


class TestStaticFileServiceNoDist:
    def test_app_starts_without_dist_dir(self, tmp_path):
        nonexistent_dir = str(tmp_path / "nonexistent_dist")
        test_app = _create_app_with_static_dir(nonexistent_dir)
        client = TestClient(test_app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_nonexistent_path_returns_404_without_dist(self, tmp_path):
        nonexistent_dir = str(tmp_path / "nonexistent_dist")
        test_app = _create_app_with_static_dir(nonexistent_dir)
        client = TestClient(test_app)
        response = client.get("/some-random-path")
        assert response.status_code == 404


class TestStaticFileServiceWithDist:
    def _setup_dist(self, tmp_path: Path) -> Path:
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        assets_dir = dist_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "index-abc123.js").write_text("console.log('hello')", encoding="utf-8")
        (assets_dir / "index-def456.css").write_text("body{color:red}", encoding="utf-8")
        html_content = '<!DOCTYPE html><html><body><div id="app"></div></body></html>'
        (dist_dir / "index.html").write_text(html_content, encoding="utf-8")
        return dist_dir

    def test_root_returns_index_html(self, tmp_path):
        dist_dir = self._setup_dist(tmp_path)
        test_app = _create_app_with_static_dir(str(dist_dir))
        client = TestClient(test_app)
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert '<div id="app">' in response.text

    def test_assets_js_file_returns_correct_content(self, tmp_path):
        dist_dir = self._setup_dist(tmp_path)
        test_app = _create_app_with_static_dir(str(dist_dir))
        client = TestClient(test_app)
        response = client.get("/assets/index-abc123.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]

    def test_assets_css_file_returns_correct_content(self, tmp_path):
        dist_dir = self._setup_dist(tmp_path)
        test_app = _create_app_with_static_dir(str(dist_dir))
        client = TestClient(test_app)
        response = client.get("/assets/index-def456.css")
        assert response.status_code == 200
        assert "css" in response.headers["content-type"]

    def test_api_routes_not_affected_by_static_files(self, tmp_path):
        dist_dir = self._setup_dist(tmp_path)
        test_app = _create_app_with_static_dir(str(dist_dir))
        client = TestClient(test_app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_nonexistent_path_returns_index_html_spa_fallback(self, tmp_path):
        dist_dir = self._setup_dist(tmp_path)
        test_app = _create_app_with_static_dir(str(dist_dir))
        client = TestClient(test_app)
        response = client.get("/nonexistent-page")
        assert response.status_code == 200
        assert '<div id="app">' in response.text

    def test_non_file_path_returns_index_html(self, tmp_path):
        dist_dir = self._setup_dist(tmp_path)
        test_app = _create_app_with_static_dir(str(dist_dir))
        client = TestClient(test_app)
        response = client.get("/some/deep/path")
        assert response.status_code == 200
        assert '<div id="app">' in response.text
