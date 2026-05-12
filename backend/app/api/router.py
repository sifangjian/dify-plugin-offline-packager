from fastapi import APIRouter

from app.api import marketplace, pack, sse

api_router = APIRouter()
api_router.include_router(marketplace.router)
api_router.include_router(pack.router)
api_router.include_router(sse.router)
