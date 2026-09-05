from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.database import engine
from api.routers.auth import router as auth_router
from api.routers.generation import router as generation_router
from api.routers.health import router as health_router
from api.routers.posts import router as posts_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="EngagedIn API", version="0.4.0", lifespan=lifespan)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(generation_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(posts_router, prefix="/api/v1")
    return app


app = create_app()
