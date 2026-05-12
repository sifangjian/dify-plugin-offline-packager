from fastapi import APIRouter

from app.api import marketplace, pack, sse

api_router = APIRouter()
api_router.include_router(marketplace.router)
api_router.include_router(pack.router)
api_router.include_router(sse.router)


@api_router.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
