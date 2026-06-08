from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from engagedin.core.models import Post
from engagedin.linkedin.client import LinkedInClient, LinkedInError


class TestLinkedInClient:
    def test_init_without_token_raises(self) -> None:
        with patch(
            "engagedin.linkedin.client.settings"
        ) as mock_settings:
            mock_settings.linkedin_access_token = ""
            with pytest.raises(LinkedInError, match="No LinkedIn access token"):
                LinkedInClient()

    def test_create_post_success(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.headers = {"x-restli-id": "urn:li:share:12345"}

        with (
            patch(
                "engagedin.linkedin.client.settings"
            ) as mock_settings,
            patch("httpx.post", return_value=mock_response) as mock_post,
        ):
            mock_settings.linkedin_access_token = "test-token"

            client = LinkedInClient()
            post = Post(
                author="urn:li:person:abc123",
                commentary="Test post content",
            )
            result = client.create_post(post)
            assert result == "urn:li:share:12345"
            mock_post.assert_called_once()

    def test_create_post_api_error(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = '{"message": "Invalid access token"}'

        with (
            patch(
                "engagedin.linkedin.client.settings"
            ) as mock_settings,
            patch("httpx.post", return_value=mock_response),
        ):
            mock_settings.linkedin_access_token = "bad-token"

            client = LinkedInClient()
            post = Post(
                author="urn:li:person:abc123",
                commentary="Test",
            )
            with pytest.raises(LinkedInError, match="LinkedIn API error"):
                client.create_post(post)

    def test_create_post_missing_urn(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.headers = {}

        with (
            patch(
                "engagedin.linkedin.client.settings"
            ) as mock_settings,
            patch("httpx.post", return_value=mock_response),
        ):
            mock_settings.linkedin_access_token = "test-token"

            client = LinkedInClient()
            post = Post(
                author="urn:li:person:abc123",
                commentary="Test",
            )
            with pytest.raises(LinkedInError, match="No post URN"):
                client.create_post(post)
