from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session

router = APIRouter()


@router.get("/healthz")
async def healthz(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception:
        return {"status": "ok", "database": "unreachable"}
