from __future__ import annotations

from functools import partial
from unittest.mock import MagicMock, patch

import httpx
import pytest
from authlib.oauth2.rfc6749 import OAuth2Token
from authlib.oauth2.rfc6749.errors import InvalidGrantError

from engagedin.linkedin.auth import (
    OAuthCallbackHandler,
    OAuthError,
    build_authorization_url,
    exchange_code_for_token,
    get_user_urn,
    run_oauth_login,
)


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
    @patch("engagedin.linkedin.auth.settings")
    def test_build_authorization_url(self, mock: MagicMock) -> None:
        mock.linkedin_client_id = "my_client_id"
        url = build_authorization_url("my_state_123")
        assert "https://www.linkedin.com/oauth/v2/authorization" in url
        assert "client_id=my_client_id" in url
        assert "state=my_state_123" in url
        assert "w_member_social" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A18473%2Fcallback" in url


class TestExchangeCodeForToken:
    @patch("engagedin.linkedin.auth.OAuth2Client")
    @patch("engagedin.linkedin.auth.settings")
    def test_exchange_code_for_token(
        self,
        mock_settings: MagicMock,
        mock_oauth2client: MagicMock,
    ) -> None:
        mock_token = OAuth2Token({"access_token": "tok_123", "expires_in": 3600})
        mock_client = MagicMock()
        mock_client.fetch_token.return_value = mock_token
        mock_oauth2client.return_value = mock_client
        mock_settings.linkedin_client_id = "cid"
        mock_settings.linkedin_client_secret = "csecret"

        token = exchange_code_for_token("auth_code_xyz")

        assert token["access_token"] == "tok_123"
        mock_client.fetch_token.assert_called_once_with(
            "https://www.linkedin.com/oauth/v2/accessToken",
            authorization_response=("http://localhost:18473/callback?code=auth_code_xyz"),
            grant_type="authorization_code",
        )


class TestGetUserUrn:
    @patch("httpx.get")
    def test_get_user_urn(self, mock: MagicMock) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {"sub": "user789"}
        mock.return_value = mock_response

        urn = get_user_urn("token_abc")

        assert urn == "urn:li:person:user789"
        mock.assert_called_once_with(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": "Bearer token_abc"},
        )

    @patch("httpx.get")
    def test_get_user_urn_raises_on_http_error(self, mock: MagicMock) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )
        mock.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            get_user_urn("bad_token")


def _grant_authorization_code(code: str | None) -> None:
    OAuthCallbackHandler.authorization_code = code


class TestRunOAuthLogin:
    @patch("engagedin.linkedin.auth.get_user_urn")
    @patch("engagedin.linkedin.auth.exchange_code_for_token")
    @patch("engagedin.linkedin.auth.webbrowser.open")
    @patch("engagedin.linkedin.auth.http.server.HTTPServer")
    @patch("engagedin.linkedin.auth.build_authorization_url")
    def test_success(
        self,
        mock_build_url: MagicMock,
        mock_callback_server: MagicMock,
        mock_webbrowser_open: MagicMock,
        mock_exchange_token: MagicMock,
        mock_get_urn: MagicMock,
    ) -> None:
        mock_build_url.return_value = "http://dummy.url/auth"
        mock_exchange_token.return_value = OAuth2Token({"access_token": "tok_1"})
        mock_get_urn.return_value = "urn:li:person:u1"
        mock_server = MagicMock()
        mock_callback_server.return_value = mock_server
        mock_server.handle_request.side_effect = partial(_grant_authorization_code, "code_x")

        access_token, user_urn = run_oauth_login()

        assert access_token == "tok_1"
        assert user_urn == "urn:li:person:u1"
        mock_webbrowser_open.assert_called_once_with("http://dummy.url/auth")
        mock_callback_server.assert_called_once_with(("localhost", 18473), OAuthCallbackHandler)
        mock_exchange_token.assert_called_once_with("code_x")
        mock_get_urn.assert_called_once_with("tok_1")
        mock_server.server_close.assert_called_once()

    @patch("engagedin.linkedin.auth.get_user_urn")
    @patch("engagedin.linkedin.auth.exchange_code_for_token")
    @patch("engagedin.linkedin.auth.webbrowser.open")
    @patch("engagedin.linkedin.auth.http.server.HTTPServer")
    @patch("engagedin.linkedin.auth.build_authorization_url")
    def test_on_url_callback(
        self,
        mock_build_url: MagicMock,
        mock_callback_server: MagicMock,
        mock_webbrowser_open: MagicMock,
        mock_exchange_token: MagicMock,
        mock_get_urn: MagicMock,
    ) -> None:
        mock_build_url.return_value = "http://dummy.url/auth"
        mock_exchange_token.return_value = OAuth2Token({"access_token": "tok_1"})
        mock_get_urn.return_value = "urn:li:person:u1"
        mock_server = MagicMock()
        mock_callback_server.return_value = mock_server
        mock_server.handle_request.side_effect = partial(_grant_authorization_code, "code_x")

        received: list[str] = []
        run_oauth_login(on_url=received.append)

        assert received == ["http://dummy.url/auth"]

    @patch("engagedin.linkedin.auth.webbrowser.open")
    @patch("engagedin.linkedin.auth.http.server.HTTPServer")
    @patch("engagedin.linkedin.auth.build_authorization_url")
    def test_no_code_raises(
        self,
        mock_build_url: MagicMock,
        mock_callback_server: MagicMock,
        mock_webbrowser_open: MagicMock,
    ) -> None:
        mock_build_url.return_value = "http://dummy.url/auth"
        mock_server = MagicMock()
        mock_callback_server.return_value = mock_server

        with pytest.raises(OAuthError, match="Authorization failed or was cancelled"):
            run_oauth_login()

    @patch("engagedin.linkedin.auth.exchange_code_for_token")
    @patch("engagedin.linkedin.auth.webbrowser.open")
    @patch("engagedin.linkedin.auth.http.server.HTTPServer")
    @patch("engagedin.linkedin.auth.build_authorization_url")
    def test_empty_token_raises(
        self,
        mock_build_url: MagicMock,
        mock_callback_server: MagicMock,
        mock_webbrowser_open: MagicMock,
        mock_exchange_token: MagicMock,
    ) -> None:
        mock_build_url.return_value = "http://dummy.url/auth"
        mock_exchange_token.return_value = OAuth2Token({"access_token": ""})
        mock_server = MagicMock()
        mock_callback_server.return_value = mock_server
        mock_server.handle_request.side_effect = partial(_grant_authorization_code, "code_x")

        with pytest.raises(OAuthError, match="Failed to obtain access token"):
            run_oauth_login()

    @patch("engagedin.linkedin.auth.exchange_code_for_token")
    @patch("engagedin.linkedin.auth.webbrowser.open")
    @patch("engagedin.linkedin.auth.http.server.HTTPServer")
    @patch("engagedin.linkedin.auth.build_authorization_url")
    def test_exchange_error_wrapped(
        self,
        mock_build_url: MagicMock,
        mock_callback_server: MagicMock,
        mock_webbrowser_open: MagicMock,
        mock_exchange_token: MagicMock,
    ) -> None:
        mock_build_url.return_value = "http://dummy.url/auth"
        mock_exchange_token.side_effect = httpx.ConnectError("connection refused")
        mock_server = MagicMock()
        mock_callback_server.return_value = mock_server
        mock_server.handle_request.side_effect = partial(_grant_authorization_code, "code_x")

        with pytest.raises(OAuthError, match="Failed to exchange the authorization code"):
            run_oauth_login()

    @patch("engagedin.linkedin.auth.exchange_code_for_token")
    @patch("engagedin.linkedin.auth.webbrowser.open")
    @patch("engagedin.linkedin.auth.http.server.HTTPServer")
    @patch("engagedin.linkedin.auth.build_authorization_url")
    def test_exchange_oauth2_error_wrapped(
        self,
        mock_build_url: MagicMock,
        mock_callback_server: MagicMock,
        mock_webbrowser_open: MagicMock,
        mock_exchange_token: MagicMock,
    ) -> None:
        mock_build_url.return_value = "http://dummy.url/auth"
        mock_exchange_token.side_effect = InvalidGrantError()
        mock_server = MagicMock()
        mock_callback_server.return_value = mock_server
        mock_server.handle_request.side_effect = partial(_grant_authorization_code, "code_x")

        with pytest.raises(OAuthError, match="Failed to exchange the authorization code"):
            run_oauth_login()

    @patch("engagedin.linkedin.auth.get_user_urn")
    @patch("engagedin.linkedin.auth.exchange_code_for_token")
    @patch("engagedin.linkedin.auth.webbrowser.open")
    @patch("engagedin.linkedin.auth.http.server.HTTPServer")
    @patch("engagedin.linkedin.auth.build_authorization_url")
    def test_profile_fetch_error_wrapped(
        self,
        mock_build_url: MagicMock,
        mock_callback_server: MagicMock,
        mock_webbrowser_open: MagicMock,
        mock_exchange_token: MagicMock,
        mock_get_urn: MagicMock,
    ) -> None:
        mock_build_url.return_value = "http://dummy.url/auth"
        mock_exchange_token.return_value = OAuth2Token({"access_token": "tok_1"})
        mock_get_urn.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401),
        )
        mock_server = MagicMock()
        mock_callback_server.return_value = mock_server
        mock_server.handle_request.side_effect = partial(_grant_authorization_code, "code_x")

        with pytest.raises(OAuthError, match="Failed to fetch your profile"):
            run_oauth_login()
