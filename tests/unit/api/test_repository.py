from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from api.models import DraftSource, PostRecord, PostStatus
from api.repositories.posts import PostRepository


def _mock_session(record: MagicMock | None = None) -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(return_value=record)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


def _mock_record(
    *,
    id: int = 1,
    topic: str = "python",
    source: DraftSource = DraftSource.STANDARD,
    status: PostStatus = PostStatus.DRAFT,
) -> MagicMock:
    record = MagicMock()
    record.id = id
    record.topic = topic
    record.source = source
    record.status = status
    record.content = "Test content"
    record.character_count = 12
    record.linkedin_post_urn = None
    record.error = None
    record.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    record.published_at = None
    return record


async def test_get_found() -> None:
    record = _mock_record()
    session = _mock_session(record)
    repo = PostRepository(session)
    result = await repo.get(1)
    assert result is record
    session.get.assert_awaited_once_with(PostRecord, 1)


async def test_get_not_found() -> None:
    session = _mock_session(None)
    repo = PostRepository(session)
    result = await repo.get(999)
    assert result is None


async def test_list_returns_items() -> None:
    record = _mock_record()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [record]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[mock_result, count_result])
    repo = PostRepository(session)
    items, total = await repo.list()
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
    repo = PostRepository(session)
    items, total = await repo.list(status=PostStatus.DRAFT)
    assert total == 1


async def test_list_with_topic_filter() -> None:
    record = _mock_record()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [record]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[mock_result, count_result])
    repo = PostRepository(session)
    items, total = await repo.list(topic="python")
    assert total == 1


async def test_add() -> None:
    session = _mock_session()
    repo = PostRepository(session)
    record = _mock_record()
    result = await repo.add(record)
    session.add.assert_called_once_with(record)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(record)
    assert result is record


async def test_update() -> None:
    record = _mock_record()
    session = _mock_session(record)
    repo = PostRepository(session)
    result = await repo.update(record)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(record)
    assert result is record


async def test_delete() -> None:
    record = _mock_record()
    session = _mock_session(record)
    repo = PostRepository(session)
    await repo.delete(record)
    session.delete.assert_awaited_once_with(record)
    session.commit.assert_awaited_once()
