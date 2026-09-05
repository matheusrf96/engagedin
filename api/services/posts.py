from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from api.models import DraftSource, PostRecord, PostStatus
from api.repositories.posts import PostRepository
from engagedin.core.engine import Engine
from engagedin.core.models import GeneratedDraft
from engagedin.linkedin.client import LinkedInError
from engagedin.llm.client import LLMConfigError
from engagedin.news.client import NewsError


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class ExternalServiceError(Exception):
    """Raised when an external call (LLM, LinkedIn, news) fails."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class PostService:
    def __init__(self, repository: PostRepository) -> None:
        self.repo = repository

    async def _generate(
        self, topic: str, source: DraftSource, days: int
    ) -> GeneratedDraft:
        engine = Engine()
        if source is DraftSource.HEADLINER:
            return await asyncio.to_thread(
                engine.generate_headliner_draft, topic=topic, days=days
            )
        return await asyncio.to_thread(engine.generate_draft, topic)

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
        if record.status is PostStatus.PUBLISHED:
            raise ConflictError(
                f"Cannot update post {post_id}: status is published"
            )
        record.content = content
        record.character_count = len(content)
        return await self.repo.update(record)

    async def publish(self, post_id: int) -> PostRecord:
        record = await self.get(post_id)
        if record.status is PostStatus.PUBLISHED:
            raise ConflictError(
                f"Cannot publish post {post_id}: status is already published"
            )

        engine = Engine()
        draft = GeneratedDraft(
            content=record.content,
            character_count=record.character_count,
        )

        try:
            post_urn = await asyncio.to_thread(engine.publish_draft, draft)
        except LinkedInError as e:
            record.status = PostStatus.FAILED
            record.error = str(e)
            await self.repo.update(record)
            raise ExternalServiceError(str(e)) from e

        record.linkedin_post_urn = post_urn
        record.status = PostStatus.PUBLISHED
        record.published_at = datetime.now(UTC)
        record.error = None
        return await self.repo.update(record)

    async def delete(self, post_id: int) -> None:
        record = await self.get(post_id)
        await self.repo.delete(record)
