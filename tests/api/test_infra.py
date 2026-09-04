from __future__ import annotations

from unittest.mock import AsyncMock, patch

from api.database import Base
from api.database import get_session as db_get_session
from api.dependencies import get_session as dep_get_session


async def test_database_base() -> None:
    assert Base.metadata is not None


async def test_database_get_session() -> None:
    mock_session = AsyncMock()
    with patch("api.database.SessionLocal") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        gen = db_get_session()
        session = await gen.__anext__()
        assert session is mock_session


async def test_dependencies_get_session() -> None:
    mock_session = AsyncMock()
    with patch("api.dependencies.SessionLocal") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        gen = dep_get_session()
        session = await gen.__anext__()
        assert session is mock_session


async def test_lifespan_dispose() -> None:
    from api.main import lifespan

    mock_app = AsyncMock()
    with patch("api.main.engine") as mock_engine:
        mock_engine.dispose = AsyncMock()
        async with lifespan(mock_app):
            pass
        mock_engine.dispose.assert_awaited_once()
