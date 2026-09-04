from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from api.models import DraftSource, PostStatus
from api.schemas import PostListResponse
from api.services.posts import ConflictError, ExternalServiceError, NotFoundError


def _mock_record(
    *,
    id: int = 1,
    topic: str = "python",
    source: DraftSource = DraftSource.STANDARD,
    status: PostStatus = PostStatus.DRAFT,
    content: str = "Test content",
    character_count: int = 12,
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
    record.linkedin_post_urn = linkedin_post_urn
    record.error = error
    record.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.published_at = published_at
    return record


@patch("api.routers.posts.PostService")
async def test_list_posts(mock_cls: MagicMock, client: AsyncClient) -> None:
    record = _mock_record()
    mock_cls.return_value.list = AsyncMock(
        return_value=PostListResponse(items=[record], total=1)
    )
    response = await client.get("/api/v1/posts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@patch("api.routers.posts.PostService")
async def test_list_posts_with_filters(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.list = AsyncMock(
        return_value=PostListResponse(items=[], total=0)
    )
    response = await client.get(
        "/api/v1/posts", params={"status": "draft", "topic": "py", "limit": 10}
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


@patch("api.routers.posts.PostService")
async def test_get_post(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.get = AsyncMock(return_value=_mock_record())
    response = await client.get("/api/v1/posts/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


@patch("api.routers.posts.PostService")
async def test_get_post_not_found(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.get = AsyncMock(
        side_effect=NotFoundError("Post 999 not found")
    )
    response = await client.get("/api/v1/posts/999")
    assert response.status_code == 404


@patch("api.routers.posts.PostService")
async def test_update_post(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.update_content = AsyncMock(
        return_value=_mock_record(content="Updated content", character_count=16)
    )
    response = await client.patch("/api/v1/posts/1", json={"content": "Updated content"})
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"


@patch("api.routers.posts.PostService")
async def test_update_post_not_found(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.update_content = AsyncMock(
        side_effect=NotFoundError("Post 999 not found")
    )
    response = await client.patch("/api/v1/posts/999", json={"content": "Updated"})
    assert response.status_code == 404


@patch("api.routers.posts.PostService")
async def test_update_post_published_conflict(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.update_content = AsyncMock(
        side_effect=ConflictError("Cannot update: status is published")
    )
    response = await client.patch("/api/v1/posts/1", json={"content": "Updated"})
    assert response.status_code == 409


async def test_update_post_empty_content(client: AsyncClient) -> None:
    response = await client.patch("/api/v1/posts/1", json={"content": ""})
    assert response.status_code == 422


@patch("api.routers.posts.PostService")
async def test_publish_post(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.publish = AsyncMock(
        return_value=_mock_record(
            status=PostStatus.PUBLISHED,
            linkedin_post_urn="urn:li:share:123",
            published_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    response = await client.post("/api/v1/posts/1/publish")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "published"
    assert data["linkedin_post_urn"] == "urn:li:share:123"


@patch("api.routers.posts.PostService")
async def test_publish_post_not_found(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.publish = AsyncMock(
        side_effect=NotFoundError("Post 999 not found")
    )
    response = await client.post("/api/v1/posts/999/publish")
    assert response.status_code == 404


@patch("api.routers.posts.PostService")
async def test_publish_post_already_published(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.publish = AsyncMock(
        side_effect=ConflictError("Cannot publish: already published")
    )
    response = await client.post("/api/v1/posts/1/publish")
    assert response.status_code == 409


@patch("api.routers.posts.PostService")
async def test_publish_post_linkedin_error(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.publish = AsyncMock(
        side_effect=ExternalServiceError("LinkedIn API error")
    )
    response = await client.post("/api/v1/posts/1/publish")
    assert response.status_code == 502
    assert "LinkedIn API error" in response.json()["detail"]


@patch("api.routers.posts.PostService")
async def test_delete_post(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.delete = AsyncMock()
    response = await client.delete("/api/v1/posts/1")
    assert response.status_code == 204


@patch("api.routers.posts.PostService")
async def test_delete_post_not_found(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.delete = AsyncMock(
        side_effect=NotFoundError("Post 999 not found")
    )
    response = await client.delete("/api/v1/posts/999")
    assert response.status_code == 404
