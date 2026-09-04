from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from engagedin.core.models import Post
from engagedin.linkedin.client import LinkedInClient, LinkedInError


@patch("engagedin.linkedin.client.settings")
def test_init_without_token_raises(
    mock_linkedin_settings: MagicMock,
) -> None:
    mock_linkedin_settings.linkedin_access_token = ""
    with pytest.raises(LinkedInError, match="No LinkedIn access token"):
        LinkedInClient()


def test_init_with_explicit_token() -> None:
    client = LinkedInClient(access_token="explicit-token")
    assert client.access_token == "explicit-token"


@patch("httpx.post")
@patch("engagedin.linkedin.client.settings")
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


@patch("httpx.post")
@patch("engagedin.linkedin.client.settings")
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


@patch("httpx.post")
@patch("engagedin.linkedin.client.settings")
def test_create_post_retries_on_transport_error(
    mock_linkedin_settings: MagicMock,
    mock_httpx_post: MagicMock,
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:12345"}
    mock_httpx_post.side_effect = [
        httpx.ConnectError("connection reset"),
        mock_response,
    ]
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()
    post = Post(author="urn:li:person:abc123", commentary="Test post content")
    result = client.create_post(post)

    assert result == "urn:li:share:12345"
    assert mock_httpx_post.call_count == 2


@patch("httpx.post")
@patch("engagedin.linkedin.client.settings")
def test_create_post_does_not_retry_mid_response_errors(
    mock_linkedin_settings: MagicMock,
    mock_httpx_post: MagicMock,
) -> None:
    mock_httpx_post.side_effect = httpx.ReadTimeout("no response received")
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()
    post = Post(author="urn:li:person:abc123", commentary="Test post content")

    with pytest.raises(LinkedInError, match="LinkedIn API error"):
        client.create_post(post)

    mock_httpx_post.assert_called_once()


@patch("httpx.post")
@patch("engagedin.linkedin.client.settings")
def test_create_post_transport_error_wrapped(
    mock_linkedin_settings: MagicMock,
    mock_httpx_post: MagicMock,
) -> None:
    mock_httpx_post.side_effect = httpx.ConnectError("connection refused")
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()
    post = Post(author="urn:li:person:abc123", commentary="Test post content")

    with pytest.raises(LinkedInError, match="LinkedIn API error"):
        client.create_post(post)

    assert mock_httpx_post.call_count == 3


@patch("httpx.post")
@patch("engagedin.linkedin.client.settings")
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


@patch("httpx.get")
@patch("engagedin.linkedin.client.settings")
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


@patch("httpx.get")
@patch("engagedin.linkedin.client.settings")
def test_get_user_info_http_error_wrapped(
    mock_linkedin_settings: MagicMock,
    mock_httpx_get: MagicMock,
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=mock_response,
    )
    mock_httpx_get.return_value = mock_response
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()
    with pytest.raises(LinkedInError, match="LinkedIn API error"):
        client.get_user_info()


@patch("httpx.get")
@patch("engagedin.linkedin.client.settings")
def test_get_user_info_http_error(
    mock_linkedin_settings: MagicMock,
    mock_httpx_get: MagicMock,
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "403 Forbidden",
        request=MagicMock(),
        response=mock_response,
    )
    mock_httpx_get.return_value = mock_response
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()

    with pytest.raises(LinkedInError, match="LinkedIn API error"):
        client.get_user_info()


@patch("httpx.get")
@patch("engagedin.linkedin.client.settings")
def test_get_user_info_transport_error_wrapped(
    mock_linkedin_settings: MagicMock,
    mock_httpx_get: MagicMock,
) -> None:
    mock_httpx_get.side_effect = httpx.ConnectError("connection refused")
    mock_linkedin_settings.linkedin_access_token = "test-token"

    client = LinkedInClient()

    with pytest.raises(LinkedInError, match="LinkedIn API error"):
        client.get_user_info()

    assert mock_httpx_get.call_count == 3
