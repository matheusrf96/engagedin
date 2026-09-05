from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.repositories.posts import PostRepository
from api.services.posts import PostService


async def get_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[PostService]:
    yield PostService(PostRepository(session))
