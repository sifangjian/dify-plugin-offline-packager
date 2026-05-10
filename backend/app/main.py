from fastapi import FastAPI

from app.api.router import api_router
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.lifespan import lifespan

app = FastAPI(
    title="Dify Plugin Offline Packager",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_router)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
