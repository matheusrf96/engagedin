from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session
from api.models import PostStatus
from api.schemas import PostListResponse, PostOut, PostUpdateRequest
from api.services.posts import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    PostService,
)

router = APIRouter(prefix="/posts")


@router.get("", response_model=PostListResponse)
async def list_posts(
    status: PostStatus | None = Query(default=None),
    topic: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> PostListResponse:
    service = PostService(session)
    return await service.list(status=status, topic=topic, limit=limit, offset=offset)


@router.get("/{post_id}", response_model=PostOut)
async def get_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
) -> PostOut:
    service = PostService(session)
    try:
        record = await service.get(post_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return PostOut.model_validate(record)


@router.patch("/{post_id}", response_model=PostOut)
async def update_post(
    post_id: int,
    request: PostUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> PostOut:
    service = PostService(session)
    try:
        record = await service.update_content(post_id, request.content)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return PostOut.model_validate(record)


@router.post("/{post_id}/publish", response_model=PostOut)
async def publish_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
) -> PostOut:
    service = PostService(session)
    try:
        record = await service.publish(post_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=e.status_code, detail=str(e)
        ) from e
    return PostOut.model_validate(record)


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    service = PostService(session)
    try:
        await service.delete(post_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
