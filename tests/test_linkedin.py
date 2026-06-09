from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from engagedin.core.models import Post
from engagedin.linkedin.client import LinkedInClient, LinkedInError


@pytest.fixture
def mock_linkedin_settings():
    with patch("engagedin.linkedin.client.settings") as m:
        yield m


@pytest.fixture
def mock_httpx_post():
    with patch("httpx.post") as m:
        yield m


@pytest.fixture
def mock_httpx_get():
    with patch("httpx.get") as m:
        yield m


def test_init_without_token_raises(
    mock_linkedin_settings: MagicMock,
) -> None:
    mock_linkedin_settings.linkedin_access_token = ""
    with pytest.raises(LinkedInError, match="No LinkedIn access token"):
        LinkedInClient()


def test_init_with_explicit_token() -> None:
    client = LinkedInClient(access_token="explicit-token")
    assert client.access_token == "explicit-token"


def test_create_post_success(
    mock_linkedin_settings: MagicMock,
    mock_httpx_post: MagicMock,
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:12345"}
    mock_httpx_post.return_value = mock_response
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()
    post = Post(author="urn:li:person:abc123", commentary="Test post content")
    result = client.create_post(post)

    assert result == "urn:li:share:12345"
    mock_httpx_post.assert_called_once()


def test_create_post_api_error(
    mock_linkedin_settings: MagicMock,
    mock_httpx_post: MagicMock,
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = '{"message": "Invalid access token"}'
    mock_httpx_post.return_value = mock_response
    mock_linkedin_settings.linkedin_access_token = "bad-token"

    client = LinkedInClient()
    post = Post(author="urn:li:person:abc123", commentary="Test")

    with pytest.raises(LinkedInError, match="LinkedIn API error"):
        client.create_post(post)


def test_create_post_missing_urn(
    mock_linkedin_settings: MagicMock,
    mock_httpx_post: MagicMock,
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.headers = {}
    mock_httpx_post.return_value = mock_response
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()
    post = Post(author="urn:li:person:abc123", commentary="Test")

    with pytest.raises(LinkedInError, match="No post URN"):
        client.create_post(post)


def test_get_user_info(
    mock_linkedin_settings: MagicMock,
    mock_httpx_get: MagicMock,
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"sub": "user789", "name": "John Doe"}
    mock_httpx_get.return_value = mock_response
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()
    info = client.get_user_info()

    assert info["sub"] == "user789"
    assert info["name"] == "John Doe"
    mock_httpx_get.assert_called_once()


def test_get_user_info_http_error(
    mock_linkedin_settings: MagicMock,
    mock_httpx_get: MagicMock,
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "403 Forbidden",
        request=MagicMock(),
        response=mock_response,
    )
    mock_httpx_get.return_value = mock_response
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()

    with pytest.raises(httpx.HTTPStatusError):
        client.get_user_info()
