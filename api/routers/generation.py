from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_service
from api.exceptions import ExternalServiceError
from api.models import DraftSource
from api.schemas import DraftCreateRequest, PostOut
from api.services.posts import PostService

router = APIRouter()


@router.post("/drafts", response_model=PostOut, status_code=201)
async def create_draft(
    request: DraftCreateRequest,
    service: PostService = Depends(get_service),
) -> PostOut:
    try:
        record = await service.create_draft(
            topic=request.topic,
            source=DraftSource(request.source),
            days=request.days,
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=e.status_code, detail=str(e)
        ) from e
    return PostOut.model_validate(record)
