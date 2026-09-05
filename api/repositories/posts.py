from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import PostRecord, PostStatus


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, post_id: int) -> PostRecord | None:
        return await self.session.get(PostRecord, post_id)

    async def list(
        self,
        *,
        status: PostStatus | None = None,
        topic: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PostRecord], int]:
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

        return items, total

    async def add(self, record: PostRecord) -> PostRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update(self, record: PostRecord) -> PostRecord:
        await self.session.commit()
        return record

    async def delete(self, record: PostRecord) -> None:
        await self.session.delete(record)
        await self.session.commit()
