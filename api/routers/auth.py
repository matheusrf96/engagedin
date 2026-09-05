import asyncio

from fastapi import APIRouter, HTTPException

from api.schemas import AuthStatusResponse
from engagedin.linkedin.client import LinkedInClient, LinkedInError

router = APIRouter(prefix="/auth")


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    try:
        client = LinkedInClient()
        info = await asyncio.to_thread(client.get_user_info)
    except LinkedInError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return AuthStatusResponse(
        name=info.get("name", "Unknown"),
        sub=info.get("sub", "Unknown"),
    )
