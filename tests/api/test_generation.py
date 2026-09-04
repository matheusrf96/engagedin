from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from api.models import DraftSource, PostStatus
from api.services.posts import ConflictError, ExternalServiceError, NotFoundError


def _mock_record(
    *,
    id: int = 1,
    topic: str = "python",
    source: DraftSource = DraftSource.STANDARD,
    status: PostStatus = PostStatus.DRAFT,
    content: str = "Generated draft content",
    character_count: int = 25,
) -> MagicMock:
    record = MagicMock()
    record.id = id
    record.topic = topic
    record.source = source
    record.status = status
    record.content = content
    record.character_count = character_count
    record.linkedin_post_urn = None
    record.error = None
    record.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.published_at = None
    return record


@patch("api.routers.generation.PostService")
async def test_create_draft_standard(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.create_draft = AsyncMock(return_value=_mock_record())
    response = await client.post("/api/v1/drafts", json={"topic": "python"})
    assert response.status_code == 201
    data = response.json()
    assert data["topic"] == "python"
    assert data["status"] == "draft"


@patch("api.routers.generation.PostService")
async def test_create_draft_headliner(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.create_draft = AsyncMock(
        return_value=_mock_record(source=DraftSource.HEADLINER)
    )
    response = await client.post(
        "/api/v1/drafts", json={"topic": "AI", "source": "headliner", "days": 3}
    )
    assert response.status_code == 201
    assert response.json()["source"] == "headliner"


@patch("api.routers.generation.PostService")
async def test_create_draft_llm_config_error(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.create_draft = AsyncMock(
        side_effect=ExternalServiceError("missing api key", status_code=400)
    )
    response = await client.post("/api/v1/drafts", json={"topic": "python"})
    assert response.status_code == 400
    assert "missing api key" in response.json()["detail"]


@patch("api.routers.generation.PostService")
async def test_create_draft_news_error(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.create_draft = AsyncMock(
        side_effect=ExternalServiceError("news source failed")
    )
    response = await client.post(
        "/api/v1/drafts", json={"topic": "AI", "source": "headliner", "days": 1}
    )
    assert response.status_code == 502


async def test_create_draft_empty_topic(client: AsyncClient) -> None:
    response = await client.post("/api/v1/drafts", json={"topic": ""})
    assert response.status_code == 422


async def test_create_draft_missing_topic(client: AsyncClient) -> None:
    response = await client.post("/api/v1/drafts", json={})
    assert response.status_code == 422


@patch("api.routers.generation.PostService")
async def test_create_draft_not_found(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.create_draft = AsyncMock(
        side_effect=NotFoundError("news not found")
    )
    response = await client.post("/api/v1/drafts", json={"topic": "AI"})
    assert response.status_code == 404


@patch("api.routers.generation.PostService")
async def test_create_draft_conflict(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.create_draft = AsyncMock(
        side_effect=ConflictError("conflict")
    )
    response = await client.post("/api/v1/drafts", json={"topic": "python"})
    assert response.status_code == 409


@patch("api.routers.generation.PostService")
async def test_create_draft_unexpected_error(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.create_draft = AsyncMock(
        side_effect=RuntimeError("unexpected")
    )
    response = await client.post("/api/v1/drafts", json={"topic": "python"})
    assert response.status_code == 500
