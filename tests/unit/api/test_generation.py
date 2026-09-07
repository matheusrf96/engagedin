from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from api.dependencies import get_service
from api.exceptions import ExternalServiceError
from api.main import create_app
from api.models import DraftSource, PostStatus


def _mock_record(
    *,
    id: int = 1,
    topic: str = "python",
    source: DraftSource = DraftSource.STANDARD,
    status: PostStatus = PostStatus.DRAFT,
    content: str = "Generated draft content",
    character_count: int = 25,
    reference_url: str | None = None,
    reference_title: str | None = None,
    reference_description: str | None = None,
    language: str | None = None,
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
    record.language = language
    record.linkedin_post_urn = None
    record.error = None
    record.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.published_at = None
    return record


def _make_client_with_mock(mock_service: AsyncMock) -> AsyncClient:
    app = create_app()
    app.dependency_overrides[get_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_create_draft_standard() -> None:
    mock_service = AsyncMock()
    mock_service.create_draft = AsyncMock(return_value=_mock_record())
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post("/api/v1/drafts", json={"topic": "python"})
    assert response.status_code == 201
    data = response.json()
    assert data["topic"] == "python"
    assert data["status"] == "draft"
    assert data["reference_url"] is None
    assert data["reference_title"] is None
    assert data["reference_description"] is None


async def test_create_draft_headliner() -> None:
    mock_service = AsyncMock()
    mock_service.create_draft = AsyncMock(
        return_value=_mock_record(
            source=DraftSource.HEADLINER,
            reference_url="https://example.com/news",
            reference_title="News title",
            reference_description="News description",
        )
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post(
            "/api/v1/drafts",
            json={"topic": "AI", "source": "headliner", "days": 3},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["source"] == "headliner"
    assert data["reference_url"] == "https://example.com/news"
    assert data["reference_title"] == "News title"
    assert data["reference_description"] == "News description"


async def test_create_draft_with_language() -> None:
    mock_service = AsyncMock()
    mock_service.create_draft = AsyncMock(
        return_value=_mock_record(language="ru", content="Пост про Python")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post(
            "/api/v1/drafts", json={"topic": "python", "language": "ru"}
        )
    assert response.status_code == 201
    data = response.json()
    assert data["language"] == "ru"
    mock_service.create_draft.assert_awaited_once_with(
        topic="python",
        source=DraftSource.STANDARD,
        days=1,
        language="ru",
    )


async def test_create_draft_without_language() -> None:
    mock_service = AsyncMock()
    mock_service.create_draft = AsyncMock(return_value=_mock_record())
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post("/api/v1/drafts", json={"topic": "python"})
    assert response.status_code == 201
    assert response.json()["language"] is None
    mock_service.create_draft.assert_awaited_once_with(
        topic="python",
        source=DraftSource.STANDARD,
        days=1,
        language=None,
    )


async def test_create_draft_invalid_language_stored_as_service_error() -> None:
    mock_service = AsyncMock()
    mock_service.create_draft = AsyncMock(
        side_effect=ExternalServiceError(
            "Invalid language tag: 'not a tag!'", status_code=400
        )
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post(
            "/api/v1/drafts", json={"topic": "python", "language": "not a tag!"}
        )
    assert response.status_code == 400
    assert "Invalid language tag" in response.json()["detail"]


async def test_create_draft_llm_config_error() -> None:
    mock_service = AsyncMock()
    mock_service.create_draft = AsyncMock(
        side_effect=ExternalServiceError("missing api key", status_code=400)
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post("/api/v1/drafts", json={"topic": "python"})
    assert response.status_code == 400
    assert "missing api key" in response.json()["detail"]


async def test_create_draft_news_error() -> None:
    mock_service = AsyncMock()
    mock_service.create_draft = AsyncMock(
        side_effect=ExternalServiceError("news source failed")
    )
    async with _make_client_with_mock(mock_service) as client:
        response = await client.post(
            "/api/v1/drafts",
            json={"topic": "AI", "source": "headliner", "days": 1},
        )
    assert response.status_code == 502


async def test_create_draft_empty_topic() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/drafts", json={"topic": ""})
    assert response.status_code == 422


async def test_create_draft_missing_topic() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/drafts", json={})
    assert response.status_code == 422
