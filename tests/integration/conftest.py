from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.database import Base
from api.dependencies import get_service, get_session
from api.main import app
from api.repositories.posts import PostRepository
from api.services.posts import PostService

_REFERENCE_TABLES: set[str] = set()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_integration_tables(
    integration_db_session: AsyncSession,
) -> AsyncIterator[None]:
    yield

    await integration_db_session.rollback()

    tables = [
        t.name
        for t in Base.metadata.sorted_tables
        if t.name not in _REFERENCE_TABLES
    ]

    if tables:
        await integration_db_session.execute(
            text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;")
        )

    await integration_db_session.commit()


@pytest_asyncio.fixture
async def async_client(
    integration_sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with integration_sessionmaker() as session:
            yield session

    async def _override_get_service() -> AsyncIterator[PostService]:
        async with integration_sessionmaker() as session:
            yield PostService(PostRepository(session))

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_service] = _override_get_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
