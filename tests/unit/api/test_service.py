from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.exceptions import ExternalServiceError
from api.models import DraftSource, PostStatus
from api.services.posts import (
    ConflictError,
    NotFoundError,
    PostService,
)


def _mock_repository(record: MagicMock | None = None) -> MagicMock:
    repo = MagicMock()
    repo.get = AsyncMock(return_value=record)
    repo.get_for_update = AsyncMock(return_value=record)
    repo.list = AsyncMock(return_value=([], 0))
    repo.add = AsyncMock(side_effect=lambda r: r)
    repo.update = AsyncMock(side_effect=lambda r: r)
    repo.delete = AsyncMock()
    return repo


def _mock_record(
    *,
    id: int = 1,
    status: PostStatus = PostStatus.DRAFT,
    content: str = "Test content",
    character_count: int = 12,
    linkedin_post_urn: str | None = None,
    error: str | None = None,
    reference_url: str | None = None,
    reference_title: str | None = None,
    reference_description: str | None = None,
) -> MagicMock:
    record = MagicMock()
    record.id = id
    record.topic = "python"
    record.source = DraftSource.STANDARD
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
    record.published_at = None
    return record


async def test_get_found() -> None:
    record = _mock_record()
    repo = _mock_repository(record)
    service = PostService(repo)
    result = await service.get(1)
    assert result is record
    repo.get.assert_awaited_once_with(1)


async def test_get_not_found() -> None:
    repo = _mock_repository(None)
    service = PostService(repo)
    with pytest.raises(NotFoundError):
        await service.get(999)
    repo.get.assert_awaited_once_with(999)


async def test_list_delegates_to_repo() -> None:
    record = _mock_record()
    repo = _mock_repository()
    repo.list = AsyncMock(return_value=([record], 1))
    service = PostService(repo)
    items, total = await service.list(status=PostStatus.DRAFT, topic="py")
    assert total == 1
    assert len(items) == 1
    repo.list.assert_awaited_once_with(
        status=PostStatus.DRAFT, topic="py", limit=20, offset=0
    )


@patch("api.services.posts.Engine")
async def test_create_draft_standard(mock_engine_cls: MagicMock) -> None:
    draft = MagicMock()
    draft.content = "Generated content"
    draft.character_count = 18
    draft.reference_url = None
    draft.reference_title = None
    draft.reference_description = None
    mock_engine_cls.return_value.generate_draft.return_value = draft

    repo = _mock_repository()
    service = PostService(repo)
    await service.create_draft("python", DraftSource.STANDARD, 1)
    repo.add.assert_awaited_once()
    added_record = repo.add.call_args[0][0]
    assert added_record.topic == "python"
    assert added_record.content == "Generated content"
    assert added_record.reference_url is None
    assert added_record.reference_title is None
    assert added_record.reference_description is None


@patch("api.services.posts.Engine")
async def test_create_draft_headliner(mock_engine_cls: MagicMock) -> None:
    draft = MagicMock()
    draft.content = "Headliner content"
    draft.character_count = 19
    draft.reference_url = "https://example.com/news"
    draft.reference_title = "News title"
    draft.reference_description = "News description"
    mock_engine_cls.return_value.generate_headliner_draft.return_value = draft

    repo = _mock_repository()
    service = PostService(repo)
    await service.create_draft("AI", DraftSource.HEADLINER, 3)
    repo.add.assert_awaited_once()
    added_record = repo.add.call_args[0][0]
    assert added_record.content == "Headliner content"
    assert added_record.reference_url == "https://example.com/news"
    assert added_record.reference_title == "News title"
    assert added_record.reference_description == "News description"


@patch("api.services.posts.Engine")
async def test_create_draft_llm_error(mock_engine_cls: MagicMock) -> None:
    from engagedin.llm.client import LLMConfigError

    mock_engine_cls.return_value.generate_draft.side_effect = LLMConfigError("no key")
    repo = _mock_repository()
    service = PostService(repo)
    with pytest.raises(ExternalServiceError) as exc_info:
        await service.create_draft("python", DraftSource.STANDARD, 1)
    assert exc_info.value.status_code == 400
    repo.add.assert_not_awaited()


@patch("api.services.posts.Engine")
async def test_create_draft_news_error(mock_engine_cls: MagicMock) -> None:
    from engagedin.news.client import NewsError

    mock_engine_cls.return_value.generate_headliner_draft.side_effect = NewsError("fail")
    repo = _mock_repository()
    service = PostService(repo)
    with pytest.raises(ExternalServiceError) as exc_info:
        await service.create_draft("AI", DraftSource.HEADLINER, 1)
    assert exc_info.value.status_code == 502
    repo.add.assert_not_awaited()


async def test_update_content() -> None:
    record = _mock_record()
    repo = _mock_repository(record)
    service = PostService(repo)
    await service.update_content(1, "New content")
    assert record.content == "New content"
    assert record.character_count == 11
    repo.update.assert_awaited_once_with(record)


async def test_update_content_published_conflict() -> None:
    record = _mock_record(status=PostStatus.PUBLISHED)
    repo = _mock_repository(record)
    service = PostService(repo)
    with pytest.raises(ConflictError):
        await service.update_content(1, "New content")
    repo.update.assert_not_awaited()


@patch("api.services.posts.Engine")
async def test_publish_success(mock_engine_cls: MagicMock) -> None:
    record = _mock_record()
    mock_engine_cls.return_value.publish_draft.return_value = "urn:li:share:123"
    repo = _mock_repository(record)
    service = PostService(repo)
    await service.publish(1)
    assert record.linkedin_post_urn == "urn:li:share:123"
    assert record.status is PostStatus.PUBLISHED
    assert record.published_at is not None
    repo.update.assert_awaited_once_with(record)


@patch("api.services.posts.Engine")
async def test_publish_rebuilds_draft_with_reference(
    mock_engine_cls: MagicMock,
) -> None:
    record = _mock_record(
        reference_url="https://example.com/news",
        reference_title="News title",
        reference_description="News description",
    )
    mock_engine_cls.return_value.publish_draft.return_value = "urn:li:share:123"
    repo = _mock_repository(record)
    service = PostService(repo)
    await service.publish(1)

    draft = mock_engine_cls.return_value.publish_draft.call_args[0][0]
    assert draft.content == "Test content"
    assert draft.character_count == 12
    assert draft.reference_url == "https://example.com/news"
    assert draft.reference_title == "News title"
    assert draft.reference_description == "News description"


@patch("api.services.posts.Engine")
async def test_publish_rebuilds_draft_without_reference(
    mock_engine_cls: MagicMock,
) -> None:
    record = _mock_record()
    mock_engine_cls.return_value.publish_draft.return_value = "urn:li:share:123"
    repo = _mock_repository(record)
    service = PostService(repo)
    await service.publish(1)

    draft = mock_engine_cls.return_value.publish_draft.call_args[0][0]
    assert draft.reference_url is None
    assert draft.reference_title is None
    assert draft.reference_description is None


async def test_publish_already_published() -> None:
    record = _mock_record(status=PostStatus.PUBLISHED)
    repo = _mock_repository(record)
    service = PostService(repo)
    with pytest.raises(ConflictError):
        await service.publish(1)
    repo.update.assert_not_awaited()


async def test_publish_not_found() -> None:
    repo = _mock_repository(None)
    service = PostService(repo)
    with pytest.raises(NotFoundError):
        await service.publish(1)
    repo.update.assert_not_awaited()


@patch("api.services.posts.Engine")
async def test_publish_uses_row_lock(mock_engine_cls: MagicMock) -> None:
    record = _mock_record()
    mock_engine_cls.return_value.publish_draft.return_value = "urn:li:share:123"
    repo = _mock_repository(record)
    service = PostService(repo)
    await service.publish(1)
    repo.get_for_update.assert_awaited_once_with(1)
    repo.get.assert_not_awaited()


@patch("api.services.posts.Engine")
async def test_publish_linkedin_error(mock_engine_cls: MagicMock) -> None:
    from engagedin.linkedin.client import LinkedInError

    record = _mock_record()
    mock_engine_cls.return_value.publish_draft.side_effect = LinkedInError("API error")
    repo = _mock_repository(record)
    service = PostService(repo)
    with pytest.raises(ExternalServiceError):
        await service.publish(1)
    assert record.status is PostStatus.FAILED
    assert record.error == "API error"
    repo.update.assert_awaited_once_with(record)


async def test_delete() -> None:
    record = _mock_record()
    repo = _mock_repository(record)
    service = PostService(repo)
    await service.delete(1)
    repo.delete.assert_awaited_once_with(record)
