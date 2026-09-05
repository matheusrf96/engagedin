from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api.services.auth import AuthService
from api.services.posts import ExternalServiceError
from engagedin.linkedin.client import LinkedInError


@patch("api.services.auth.LinkedInClient")
async def test_get_status_success(mock_cls: MagicMock) -> None:
    mock_cls.return_value.get_user_info.return_value = {
        "name": "Matheus",
        "sub": "abc123",
    }
    info = await AuthService().get_status()
    assert info == {"name": "Matheus", "sub": "abc123"}


@patch("api.services.auth.LinkedInClient")
async def test_get_status_missing_fields(mock_cls: MagicMock) -> None:
    mock_cls.return_value.get_user_info.return_value = {}
    info = await AuthService().get_status()
    assert info == {"name": "Unknown", "sub": "Unknown"}


@patch("api.services.auth.LinkedInClient")
async def test_get_status_linkedin_error(mock_cls: MagicMock) -> None:
    mock_cls.return_value.get_user_info.side_effect = LinkedInError("No token")
    with pytest.raises(ExternalServiceError) as exc_info:
        await AuthService().get_status()
    assert exc_info.value.status_code == 502
    assert "No token" in str(exc_info.value)
