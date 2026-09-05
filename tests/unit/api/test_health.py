from __future__ import annotations

from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from api.dependencies import get_session
from api.main import create_app


async def test_healthz_reachable() -> None:
    mock_session = AsyncMock()

    app = create_app()
    app.dependency_overrides[get_session] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_healthz_db_unreachable() -> None:
    mock_session = AsyncMock()
    mock_session.execute.side_effect = SQLAlchemyError("connection refused")

    app = create_app()
    app.dependency_overrides[get_session] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "degraded"
    assert response.json()["detail"]["database"] == "unreachable"
