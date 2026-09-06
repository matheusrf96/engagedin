from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from api.dependencies import get_service
from api.exceptions import ExternalServiceError
from api.main import create_app
from api.models import DraftSource, PostStatus
from api.services.posts import ConflictError, NotFoundError


def _mock_record(
    *,
    id: int = 1,
    topic: str = "python",
    source: DraftSource = DraftSource.STANDARD,
    status: PostStatus = PostStatus.DRAFT,
    content: str = "Test content",
    character_count: int = 12,
    reference_url: str | None = None,
    reference_title: str | None = None,
    reference_description: str | None = None,
    linkedin_post_urn: str | None = None,
    error: str | None = None,
    published_at: datetime | None = None,
) -> MagicMock:
    record = MagicMock()
    record.id = id
    record.topic = topic
    record.source = source
    record.status = status
    record.content = content
    record.character_count = character_count
    record.reference_url = reference_url
    record.reference_title = reference_title
    record.reference_description = reference_description
    record.linkedin_post_urn = linkedin_post_urn
    record.error = error
    record.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.published_at = published_at
    return record


def _make_client_with_mock(mock_service: AsyncMock) -> AsyncClient:
    app = create_app()
    app.dependency_overrides[get_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_list_posts() -> None:
    record = _mock_record()
    mock_service = AsyncMock()
    mock_service.list = AsyncMock(return_value=([record], 1))
    async with _make_client_with_mock(mock_service) as client:
        response = await client.get("/api/v1/posts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


async def test_list_posts_with_filters() -> None:
    mock_service = AsyncMock()
    mock_service.list = AsyncMock(return_value=([], 0))
    async with _make_client_with_mock(mock_service) as client:
        response = await client.get(
            "/api/v1/posts", params={"status": "draft", "topic": "py", "limit": 10}
        )
    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_get_post() -> None:
    record = _mock_record()
    mock_service = AsyncMock()
    mock_service.get = AsyncMock(return_value=record)
    async with _make_client_with_mock(mock_service) as client:
        response = await client.get("/api/v1/posts/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


async def test_get_post_not_found() -> None:
    mock_service = AsyncMock()
    mock_service.get = AsyncMock(
        side_effect=NotFoundError("Post 999 not found")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.get("/api/v1/posts/999")
    assert response.status_code == 404


async def test_update_post() -> None:
    record = _mock_record(content="Updated content", character_count=16)
    mock_service = AsyncMock()
    mock_service.update_content = AsyncMock(return_value=record)
    async with _make_client_with_mock(mock_service) as client:
        response = await client.patch(
            "/api/v1/posts/1", json={"content": "Updated content"}
        )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"


async def test_update_post_not_found() -> None:
    mock_service = AsyncMock()
    mock_service.update_content = AsyncMock(
        side_effect=NotFoundError("Post 999 not found")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.patch(
            "/api/v1/posts/999", json={"content": "Updated"}
        )
    assert response.status_code == 404


async def test_update_post_published_conflict() -> None:
    mock_service = AsyncMock()
    mock_service.update_content = AsyncMock(
        side_effect=ConflictError("Cannot update: status is published")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.patch("/api/v1/posts/1", json={"content": "Updated"})
    assert response.status_code == 409


async def test_update_post_empty_content() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch("/api/v1/posts/1", json={"content": ""})
    assert response.status_code == 422


async def test_publish_post() -> None:
    record = _mock_record(
        status=PostStatus.PUBLISHED,
        linkedin_post_urn="urn:li:share:123",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    mock_service = AsyncMock()
    mock_service.publish = AsyncMock(return_value=record)
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post("/api/v1/posts/1/publish")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "published"
    assert data["linkedin_post_urn"] == "urn:li:share:123"


async def test_publish_post_not_found() -> None:
    mock_service = AsyncMock()
    mock_service.publish = AsyncMock(
        side_effect=NotFoundError("Post 999 not found")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post("/api/v1/posts/999/publish")
    assert response.status_code == 404


async def test_publish_post_already_published() -> None:
    mock_service = AsyncMock()
    mock_service.publish = AsyncMock(
        side_effect=ConflictError("Cannot publish: already published")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post("/api/v1/posts/1/publish")
    assert response.status_code == 409


async def test_publish_post_linkedin_error() -> None:
    mock_service = AsyncMock()
    mock_service.publish = AsyncMock(
        side_effect=ExternalServiceError("LinkedIn API error")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post("/api/v1/posts/1/publish")
    assert response.status_code == 502
    assert "LinkedIn API error" in response.json()["detail"]


async def test_delete_post() -> None:
    mock_service = AsyncMock()
    mock_service.delete = AsyncMock()
    async with _make_client_with_mock(mock_service) as client:
        response = await client.delete("/api/v1/posts/1")
    assert response.status_code == 204


async def test_delete_post_not_found() -> None:
    mock_service = AsyncMock()
    mock_service.delete = AsyncMock(
        side_effect=NotFoundError("Post 999 not found")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.delete("/api/v1/posts/999")
    assert response.status_code == 404
