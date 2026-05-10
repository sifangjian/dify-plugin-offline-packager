from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.httpx_client = AsyncClient(timeout=10.0)
    yield
    await app.state.httpx_client.aclose()
