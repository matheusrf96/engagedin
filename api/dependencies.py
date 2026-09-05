from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import SessionLocal
from api.repositories.posts import PostRepository
from api.services.posts import PostService


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def get_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[PostService]:
    yield PostService(PostRepository(session))
