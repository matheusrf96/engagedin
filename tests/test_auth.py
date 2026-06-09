from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import httpx
import pytest
from authlib.oauth2.rfc6749 import OAuth2Token

from engagedin.linkedin.auth import (
    OAuthCallbackHandler,
    build_authorization_url,
    exchange_code_for_token,
    get_user_urn,
)


@pytest.fixture
def mock_auth_settings() -> Generator[MagicMock, None, None]:
    with patch("engagedin.linkedin.auth.settings") as m:
        yield m


@pytest.fixture
def mock_oauth2client() -> Generator[MagicMock, None, None]:
    with patch("engagedin.linkedin.auth.OAuth2Client") as m:
        yield m


@pytest.fixture
def mock_httpx_get() -> Generator[MagicMock, None, None]:
    with patch("httpx.get") as m:
        yield m


class TestOAuthCallbackHandler:
    def setup_method(self) -> None:
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.expected_state = ""

    @staticmethod
    def _make_handler() -> OAuthCallbackHandler:
        handler = object.__new__(OAuthCallbackHandler)
        handler.path = "/"
        handler.headers = MagicMock()
        handler.command = "GET"
        handler.request_version = "HTTP/1.0"
        handler.close_connection = False
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        return handler

    def test_successful_callback(self) -> None:
        OAuthCallbackHandler.expected_state = "state123"
        handler = self._make_handler()
        handler.path = "/callback?state=state123&code=auth_code_xyz"

        handler.do_GET()

        assert OAuthCallbackHandler.authorization_code == "auth_code_xyz"
        handler.send_response.assert_called_with(200)

    def test_state_mismatch(self) -> None:
        OAuthCallbackHandler.expected_state = "expected_state"
        handler = self._make_handler()
        handler.path = "/callback?state=wrong_state&code=code"

        handler.do_GET()

        assert OAuthCallbackHandler.authorization_code is None
        handler.send_response.assert_called_with(400)

    def test_no_code_in_callback(self) -> None:
        OAuthCallbackHandler.expected_state = "state123"
        handler = self._make_handler()
        handler.path = "/callback?state=state123"

        handler.do_GET()

        assert OAuthCallbackHandler.authorization_code is None
        handler.send_response.assert_called_with(400)


class TestBuildAuthorizationUrl:
    def test_build_authorization_url(
        self, mock_auth_settings: MagicMock
    ) -> None:
        mock_auth_settings.linkedin_client_id = "my_client_id"
        url = build_authorization_url("my_state_123")
        assert "https://www.linkedin.com/oauth/v2/authorization" in url
        assert "client_id=my_client_id" in url
        assert "state=my_state_123" in url
        assert "w_member_social" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A18473%2Fcallback" in url


class TestExchangeCodeForToken:
    def test_exchange_code_for_token(
        self,
        mock_auth_settings: MagicMock,
        mock_oauth2client: MagicMock,
    ) -> None:
        mock_token = OAuth2Token({"access_token": "tok_123", "expires_in": 3600})
        mock_client = MagicMock()
        mock_client.fetch_token.return_value = mock_token
        mock_oauth2client.return_value = mock_client
        mock_auth_settings.linkedin_client_id = "cid"
        mock_auth_settings.linkedin_client_secret = "csecret"

        token = exchange_code_for_token("auth_code_xyz")

        assert token["access_token"] == "tok_123"
        mock_client.fetch_token.assert_called_once_with(
            "https://www.linkedin.com/oauth/v2/accessToken",
            authorization_response=(
                "http://localhost:18473/callback?code=auth_code_xyz"
            ),
            grant_type="authorization_code",
        )


class TestGetUserUrn:
    def test_get_user_urn(self, mock_httpx_get: MagicMock) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {"sub": "user789"}
        mock_httpx_get.return_value = mock_response

        urn = get_user_urn("token_abc")

        assert urn == "urn:li:person:user789"
        mock_httpx_get.assert_called_once_with(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": "Bearer token_abc"},
        )

    def test_get_user_urn_raises_on_http_error(
        self, mock_httpx_get: MagicMock
    ) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )
        mock_httpx_get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            get_user_urn("bad_token")
