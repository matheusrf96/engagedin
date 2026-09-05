from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from api.exceptions import ExternalServiceError
from api.models import DraftSource, PostRecord, PostStatus
from api.repositories.posts import PostRepository
from engagedin.core.engine import Engine
from engagedin.core.models import GeneratedDraft
from engagedin.linkedin.client import LinkedInError
from engagedin.llm.client import LLMConfigError
from engagedin.news.client import NewsError


def _utcnow() -> datetime:
    """Naive UTC now, matching the DB's timestamp without time zone columns."""
    return datetime.now(UTC).replace(tzinfo=None)


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class PostService:
    def __init__(self, repository: PostRepository) -> None:
        self.repo = repository

    async def _generate(
        self, topic: str, source: DraftSource, days: int
    ) -> GeneratedDraft:
        if source is DraftSource.HEADLINER:
            return await asyncio.to_thread(
                self._generate_headliner, topic, days
            )
        return await asyncio.to_thread(self._generate_standard, topic)

    def _generate_standard(self, topic: str) -> GeneratedDraft:
        return Engine().generate_draft(topic)

    def _generate_headliner(self, topic: str, days: int) -> GeneratedDraft:
        return Engine().generate_headliner_draft(topic=topic, days=days)

    async def create_draft(
        self, topic: str, source: DraftSource, days: int
    ) -> PostRecord:
        try:
            draft = await self._generate(topic, source, days)
        except LLMConfigError as e:
            raise ExternalServiceError(str(e), status_code=400) from e
        except NewsError as e:
            raise ExternalServiceError(str(e)) from e

        record = PostRecord(
            topic=topic,
            source=source,
            status=PostStatus.DRAFT,
            content=draft.content,
            character_count=draft.character_count,
        )
        return await self.repo.add(record)

    async def get(self, post_id: int) -> PostRecord:
        record = await self.repo.get(post_id)
        if record is None:
            raise NotFoundError(f"Post {post_id} not found")
        return record

    async def list(
        self,
        *,
        status: PostStatus | None = None,
        topic: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PostRecord], int]:
        return await self.repo.list(
            status=status, topic=topic, limit=limit, offset=offset
        )

    async def update_content(self, post_id: int, content: str) -> PostRecord:
        record = await self.get(post_id)
        if record.status == PostStatus.PUBLISHED:
            raise ConflictError(
                f"Cannot update post {post_id}: status is published"
            )
        record.content = content
        record.character_count = len(content)
        record.updated_at = _utcnow()
        return await self.repo.update(record)

    async def publish(self, post_id: int) -> PostRecord:
        record = await self.get(post_id)
        if record.status == PostStatus.PUBLISHED:
            raise ConflictError(
                f"Cannot publish post {post_id}: status is already published"
            )

        try:
            post_urn = await asyncio.to_thread(
                self._publish_draft, record.content, record.character_count
            )
        except LinkedInError as e:
            record.status = PostStatus.FAILED
            record.error = str(e)
            record.updated_at = _utcnow()
            await self.repo.update(record)
            raise ExternalServiceError(str(e)) from e

        record.linkedin_post_urn = post_urn
        record.status = PostStatus.PUBLISHED
        record.published_at = _utcnow()
        record.updated_at = _utcnow()
        record.error = None
        return await self.repo.update(record)

    def _publish_draft(self, content: str, character_count: int) -> str:
        draft = GeneratedDraft(content=content, character_count=character_count)
        return Engine().publish_draft(draft)

    async def delete(self, post_id: int) -> None:
        record = await self.get(post_id)
        await self.repo.delete(record)
