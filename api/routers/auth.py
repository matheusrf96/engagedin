from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import AuthStatusResponse
from api.services.auth import AuthService
from api.services.posts import ExternalServiceError

router = APIRouter(prefix="/auth")


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    try:
        info = await AuthService().get_status()
    except ExternalServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    return AuthStatusResponse(**info)
