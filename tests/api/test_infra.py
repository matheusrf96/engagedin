from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from api.database import Base
from api.database import get_session as db_get_session
from api.dependencies import get_session as dep_get_session
from api.main import lifespan


async def test_database_base() -> None:
    assert Base.metadata is not None


@patch("api.database.SessionLocal")
async def test_database_get_session(mock_cls: MagicMock) -> None:
    mock_session = AsyncMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    gen = db_get_session()
    session = await gen.__anext__()
    assert session is mock_session


@patch("api.dependencies.SessionLocal")
async def test_dependencies_get_session(mock_cls: MagicMock) -> None:
    mock_session = AsyncMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    gen = dep_get_session()
    session = await gen.__anext__()
    assert session is mock_session


@patch("api.main.engine")
async def test_lifespan_dispose(mock_engine: MagicMock) -> None:
    mock_app = AsyncMock()
    mock_engine.dispose = AsyncMock()
    async with lifespan(mock_app):
        pass
    mock_engine.dispose.assert_awaited_once()
