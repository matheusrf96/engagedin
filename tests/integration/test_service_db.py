from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import DraftSource, PostRecord, PostStatus
from api.repositories.posts import PostRepository
from api.services.posts import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    PostService,
)
from engagedin.core.models import GeneratedDraft
from engagedin.linkedin.client import LinkedInError


def _draft(content: str = "Test content") -> GeneratedDraft:
    return GeneratedDraft(content=content, character_count=len(content))


async def test_create_draft_persists(
    integration_db_session: AsyncSession,
) -> None:
    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.generate_draft.return_value = _draft("Hello")
        service = PostService(PostRepository(integration_db_session))
        record = await service.create_draft("python", DraftSource.STANDARD, 1)

    assert record.id is not None
    assert record.topic == "python"
    assert record.source is DraftSource.STANDARD
    assert record.status is PostStatus.DRAFT
    assert record.content == "Hello"
    assert record.character_count == 5

    db_record = await integration_db_session.get(PostRecord, record.id)
    assert db_record is not None
    assert db_record.topic == "python"


async def test_create_draft_headliner_persists(
    integration_db_session: AsyncSession,
) -> None:
    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.generate_headliner_draft.return_value = _draft(
            "Headliner"
        )
        service = PostService(PostRepository(integration_db_session))
        record = await service.create_draft("AI", DraftSource.HEADLINER, 3)

    assert record.source is DraftSource.HEADLINER
    assert record.content == "Headliner"


async def test_get_returns_record(
    integration_db_session: AsyncSession,
) -> None:
    record = PostRecord(
        topic="test",
        source=DraftSource.STANDARD,
        status=PostStatus.DRAFT,
        content="Get me",
        character_count=6,
    )
    integration_db_session.add(record)
    await integration_db_session.commit()
    await integration_db_session.refresh(record)

    service = PostService(PostRepository(integration_db_session))
    result = await service.get(record.id)
    assert result.id == record.id
    assert result.content == "Get me"


async def test_get_unknown_raises(
    integration_db_session: AsyncSession,
) -> None:
    service = PostService(PostRepository(integration_db_session))
    with pytest.raises(NotFoundError):
        await service.get(99999)


async def test_list_filters_by_status_and_topic(
    integration_db_session: AsyncSession,
) -> None:
    for topic, status in [
        ("python", PostStatus.DRAFT),
        ("python", PostStatus.PUBLISHED),
        ("rust", PostStatus.DRAFT),
    ]:
        integration_db_session.add(
            PostRecord(
                topic=topic,
                source=DraftSource.STANDARD,
                status=status,
                content="x",
                character_count=1,
            )
        )
    await integration_db_session.commit()

    service = PostService(PostRepository(integration_db_session))

    items, total = await service.list()
    assert total == 3

    items, total = await service.list(status=PostStatus.DRAFT)
    assert total == 2

    items, total = await service.list(topic="python")
    assert total == 2

    items, total = await service.list(status=PostStatus.DRAFT, topic="rust")
    assert total == 1


async def test_update_content_recomputes_count(
    integration_db_session: AsyncSession,
) -> None:
    record = PostRecord(
        topic="update",
        source=DraftSource.STANDARD,
        status=PostStatus.DRAFT,
        content="old",
        character_count=3,
    )
    integration_db_session.add(record)
    await integration_db_session.commit()
    await integration_db_session.refresh(record)

    service = PostService(PostRepository(integration_db_session))
    updated = await service.update_content(record.id, "new content here")
    assert updated.content == "new content here"
    assert updated.character_count == len("new content here")


async def test_update_published_conflicts(
    integration_db_session: AsyncSession,
) -> None:
    record = PostRecord(
        topic="pub",
        source=DraftSource.STANDARD,
        status=PostStatus.PUBLISHED,
        content="published",
        character_count=9,
        linkedin_post_urn="urn:li:share:123",
        published_at=datetime(2026, 1, 1),
    )
    integration_db_session.add(record)
    await integration_db_session.commit()
    await integration_db_session.refresh(record)

    service = PostService(PostRepository(integration_db_session))
    with pytest.raises(ConflictError):
        await service.update_content(record.id, "new")


async def test_publish_success_persists_urn(
    integration_db_session: AsyncSession,
) -> None:
    record = PostRecord(
        topic="publish",
        source=DraftSource.STANDARD,
        status=PostStatus.DRAFT,
        content="Ready to publish",
        character_count=16,
    )
    integration_db_session.add(record)
    await integration_db_session.commit()
    await integration_db_session.refresh(record)

    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.publish_draft.return_value = "urn:li:share:abc"
        service = PostService(PostRepository(integration_db_session))
        result = await service.publish(record.id)

    assert result.linkedin_post_urn == "urn:li:share:abc"
    assert result.status is PostStatus.PUBLISHED
    assert result.published_at is not None


async def test_publish_failure_persists_failed(
    integration_db_session: AsyncSession,
) -> None:
    record = PostRecord(
        topic="fail",
        source=DraftSource.STANDARD,
        status=PostStatus.DRAFT,
        content="Will fail",
        character_count=9,
    )
    integration_db_session.add(record)
    await integration_db_session.commit()
    await integration_db_session.refresh(record)

    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.publish_draft.side_effect = LinkedInError(
            "API error"
        )
        service = PostService(PostRepository(integration_db_session))
        with pytest.raises(ExternalServiceError):
            await service.publish(record.id)

    db_record = await integration_db_session.get(PostRecord, record.id)
    assert db_record.status is PostStatus.FAILED
    assert db_record.error == "API error"


async def test_publish_after_failure_succeeds(
    integration_db_session: AsyncSession,
) -> None:
    record = PostRecord(
        topic="retry",
        source=DraftSource.STANDARD,
        status=PostStatus.FAILED,
        content="Try again",
        character_count=9,
        error="previous error",
    )
    integration_db_session.add(record)
    await integration_db_session.commit()
    await integration_db_session.refresh(record)

    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.publish_draft.return_value = "urn:li:share:retry"
        service = PostService(PostRepository(integration_db_session))
        result = await service.publish(record.id)

    assert result.status is PostStatus.PUBLISHED
    assert result.linkedin_post_urn == "urn:li:share:retry"
    assert result.error is None


async def test_delete_removes_record(
    integration_db_session: AsyncSession,
) -> None:
    record = PostRecord(
        topic="delete",
        source=DraftSource.STANDARD,
        status=PostStatus.DRAFT,
        content="Delete me",
        character_count=9,
    )
    integration_db_session.add(record)
    await integration_db_session.commit()
    record_id = record.id

    service = PostService(PostRepository(integration_db_session))
    await service.delete(record_id)

    deleted = await integration_db_session.get(PostRecord, record_id)
    assert deleted is None

    with pytest.raises(NotFoundError):
        await service.delete(record_id)
