from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models import DraftSource, PostStatus
from api.services.posts import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    PostService,
)


def _mock_session(record: MagicMock | None = None) -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(return_value=record)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session


def _mock_record(
    *,
    id: int = 1,
    status: PostStatus = PostStatus.DRAFT,
    content: str = "Test content",
    character_count: int = 12,
    linkedin_post_urn: str | None = None,
    error: str | None = None,
) -> MagicMock:
    record = MagicMock()
    record.id = id
    record.topic = "python"
    record.source = DraftSource.STANDARD
    record.status = status
    record.content = content
    record.character_count = character_count
    record.linkedin_post_urn = linkedin_post_urn
    record.error = error
    record.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.published_at = None
    return record


async def test_get_found() -> None:
    record = _mock_record()
    session = _mock_session(record)
    service = PostService(session)
    result = await service.get(1)
    assert result is record


async def test_get_not_found() -> None:
    session = _mock_session(None)
    service = PostService(session)
    with pytest.raises(NotFoundError):
        await service.get(999)


async def test_list_returns_items() -> None:
    record = _mock_record()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [record]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[mock_result, count_result])
    service = PostService(session)
    items, total = await service.list()
    assert total == 1
    assert len(items) == 1


async def test_list_with_status_filter() -> None:
    record = _mock_record()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [record]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[mock_result, count_result])
    service = PostService(session)
    items, total = await service.list(status=PostStatus.DRAFT)
    assert total == 1


async def test_list_with_topic_filter() -> None:
    record = _mock_record()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [record]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[mock_result, count_result])
    service = PostService(session)
    items, total = await service.list(topic="python")
    assert total == 1


@patch("api.services.posts.Engine")
async def test_create_draft_standard(mock_engine_cls: MagicMock) -> None:
    draft = MagicMock()
    draft.content = "Generated content"
    draft.character_count = 18
    mock_engine_cls.return_value.generate_draft.return_value = draft

    session = _mock_session()
    service = PostService(session)
    await service.create_draft("python", DraftSource.STANDARD, 1)
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@patch("api.services.posts.Engine")
async def test_create_draft_headliner(mock_engine_cls: MagicMock) -> None:
    draft = MagicMock()
    draft.content = "Headliner content"
    draft.character_count = 19
    mock_engine_cls.return_value.generate_headliner_draft.return_value = draft

    session = _mock_session()
    service = PostService(session)
    await service.create_draft("AI", DraftSource.HEADLINER, 3)
    session.add.assert_called_once()


@patch("api.services.posts.Engine")
async def test_create_draft_llm_error(mock_engine_cls: MagicMock) -> None:
    from engagedin.llm.client import LLMConfigError

    mock_engine_cls.return_value.generate_draft.side_effect = LLMConfigError("no key")
    session = _mock_session()
    service = PostService(session)
    with pytest.raises(ExternalServiceError) as exc_info:
        await service.create_draft("python", DraftSource.STANDARD, 1)
    assert exc_info.value.status_code == 400


@patch("api.services.posts.Engine")
async def test_create_draft_news_error(mock_engine_cls: MagicMock) -> None:
    from engagedin.news.client import NewsError

    mock_engine_cls.return_value.generate_headliner_draft.side_effect = NewsError("fail")
    session = _mock_session()
    service = PostService(session)
    with pytest.raises(ExternalServiceError) as exc_info:
        await service.create_draft("AI", DraftSource.HEADLINER, 1)
    assert exc_info.value.status_code == 502


async def test_update_content() -> None:
    record = _mock_record()
    session = _mock_session(record)
    service = PostService(session)
    await service.update_content(1, "New content")
    assert record.content == "New content"
    assert record.character_count == 11
    session.commit.assert_awaited_once()


async def test_update_content_published_conflict() -> None:
    record = _mock_record(status=PostStatus.PUBLISHED)
    session = _mock_session(record)
    service = PostService(session)
    with pytest.raises(ConflictError):
        await service.update_content(1, "New content")


@patch("api.services.posts.Engine")
async def test_publish_success(mock_engine_cls: MagicMock) -> None:
    record = _mock_record()
    mock_engine_cls.return_value.publish_draft.return_value = "urn:li:share:123"
    session = _mock_session(record)
    service = PostService(session)
    await service.publish(1)
    assert record.linkedin_post_urn == "urn:li:share:123"
    assert record.status is PostStatus.PUBLISHED
    assert record.published_at is not None


async def test_publish_already_published() -> None:
    record = _mock_record(status=PostStatus.PUBLISHED)
    session = _mock_session(record)
    service = PostService(session)
    with pytest.raises(ConflictError):
        await service.publish(1)


@patch("api.services.posts.Engine")
async def test_publish_linkedin_error(mock_engine_cls: MagicMock) -> None:
    from engagedin.linkedin.client import LinkedInError

    record = _mock_record()
    mock_engine_cls.return_value.publish_draft.side_effect = LinkedInError("API error")
    session = _mock_session(record)
    service = PostService(session)
    with pytest.raises(ExternalServiceError):
        await service.publish(1)
    assert record.status is PostStatus.FAILED
    assert record.error == "API error"


async def test_delete() -> None:
    record = _mock_record()
    session = _mock_session(record)
    service = PostService(session)
    await service.delete(1)
    session.delete.assert_called_once_with(record)
    session.commit.assert_awaited_once()
