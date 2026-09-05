from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from api.services.posts import ExternalServiceError


@patch("api.routers.auth.AuthService")
async def test_auth_status_authenticated(
    mock_cls: MagicMock, client: AsyncClient
) -> None:
    mock_cls.return_value.get_status = AsyncMock(
        return_value={"name": "Matheus", "sub": "abc123"}
    )
    response = await client.get("/api/v1/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Matheus"
    assert data["sub"] == "abc123"


@patch("api.routers.auth.AuthService")
async def test_auth_status_not_authenticated(
    mock_cls: MagicMock, client: AsyncClient
) -> None:
    mock_cls.return_value.get_status = AsyncMock(
        side_effect=ExternalServiceError("No token")
    )
    response = await client.get("/api/v1/auth/status")
    assert response.status_code == 502
    assert "No token" in response.json()["detail"]
