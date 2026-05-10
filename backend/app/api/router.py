from fastapi import APIRouter

from app.api import marketplace

api_router = APIRouter()
api_router.include_router(marketplace.router)
