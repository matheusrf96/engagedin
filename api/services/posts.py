from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import DraftSource, PostRecord, PostStatus
from api.schemas import PostListResponse
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
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get(self, post_id: int) -> PostRecord:
        record = await self.session.get(PostRecord, post_id)
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
    ) -> PostListResponse:
        stmt = select(PostRecord)
        count_stmt = select(func.count(PostRecord.id))

        if status is not None:
            stmt = stmt.where(PostRecord.status == status)
            count_stmt = count_stmt.where(PostRecord.status == status)

        if topic is not None:
            stmt = stmt.where(PostRecord.topic.ilike(f"%{topic}%"))
            count_stmt = count_stmt.where(PostRecord.topic.ilike(f"%{topic}%"))

        stmt = stmt.order_by(
            PostRecord.created_at.desc(), PostRecord.id.desc()
        ).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        return PostListResponse(items=items, total=total)

    async def update_content(self, post_id: int, content: str) -> PostRecord:
        record = await self.get(post_id)
        if record.status is PostStatus.PUBLISHED:
            raise ConflictError(
                f"Cannot update post {post_id}: status is published"
            )
        record.content = content
        record.character_count = len(content)
        record.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(record)
        return record

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
            await self.session.commit()
            await self.session.refresh(record)
            raise ExternalServiceError(str(e)) from e

        record.linkedin_post_urn = post_urn
        record.status = PostStatus.PUBLISHED
        record.published_at = datetime.now(UTC)
        record.error = None
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def delete(self, post_id: int) -> None:
        record = await self.get(post_id)
        await self.session.delete(record)
        await self.session.commit()
