from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session
from api.models import DraftSource
from api.schemas import DraftCreateRequest, PostOut
from api.services.posts import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    PostService,
)

router = APIRouter()


@router.post("/drafts", response_model=PostOut, status_code=201)
async def create_draft(
    request: DraftCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> PostOut:
    service = PostService(session)
    try:
        record = await service.create_draft(
            topic=request.topic,
            source=DraftSource(request.source),
            days=request.days,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=e.status_code, detail=str(e)
        ) from e
    return PostOut.model_validate(record)
