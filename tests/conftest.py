from __future__ import annotations

import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from api.database import Base
from api.dependencies import get_session
from api.main import create_app


def _get_test_db_url() -> str:
    """Get PostgreSQL test database URL from environment or use default."""
    if db_url := os.getenv("DATABASE_URL"):
        return db_url.replace("/engagedin", "/engagedin_test", 1)
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    return (
        f"postgresql+asyncpg://engagedin:engagedin@localhost:"
        f"{postgres_port}/engagedin_test"
    )


# ---------------------------------------------------------------------------
# Unit test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def app(mock_session: AsyncMock):
    application = create_app()
    application.dependency_overrides[get_session] = lambda: mock_session
    return application


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Integration test fixtures (PostgreSQL)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def integration_db_engine():
    """Create and manage a test database for this test session.

    Creates a unique database, builds schema via create_all, yields the
    engine, then drops everything on teardown. Skips gracefully if
    PostgreSQL is unavailable.
    """
    base_url = _get_test_db_url().replace("engagedin_test", "postgres")
    test_db_name = f"engagedin_test_{uuid4().hex[:8]}"
    test_db_url = _get_test_db_url().replace("engagedin_test", test_db_name)

    try:
        engine = create_async_engine(
            base_url, echo=False, poolclass=NullPool, isolation_level="AUTOCOMMIT"
        )
        async with engine.connect() as conn:
            await conn.execute(
                text(f"CREATE DATABASE {test_db_name} WITH ENCODING 'utf8';")
            )
        await engine.dispose()
    except OSError as e:
        pytest.skip(
            f"PostgreSQL not available for integration tests: {e}\n"
            "  Start it with: make integration-test-up\n"
            "  Or run unit tests only: make unit-test"
        )

    test_engine = create_async_engine(test_db_url, echo=False, poolclass=NullPool)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()

    cleanup_engine = create_async_engine(
        base_url, echo=False, poolclass=NullPool, isolation_level="AUTOCOMMIT"
    )
    async with cleanup_engine.connect() as conn:
        await conn.execute(
            text(
                f"""SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{test_db_name}'
                AND pid <> pg_backend_pid();"""
            )
        )
        await conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name};"))
    await cleanup_engine.dispose()


@pytest_asyncio.fixture
async def integration_db_session(
    integration_db_engine,
) -> AsyncIterator[AsyncSession]:
    """Create a test database session for integration tests."""
    async with AsyncSession(
        integration_db_engine, expire_on_commit=False
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def integration_sessionmaker(
    integration_db_engine,
) -> async_sessionmaker[AsyncSession]:
    """Provide an async_sessionmaker bound to the integration engine."""
    return async_sessionmaker(
        bind=integration_db_engine, expire_on_commit=False
    )
