from __future__ import annotations

from httpx import AsyncClient


async def test_healthz_reachable(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_healthz_db_unreachable(client: AsyncClient, mock_session) -> None:
    mock_session.execute.side_effect = Exception("connection refused")
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["database"] == "unreachable"
