from __future__ import annotations

import http.server
import secrets
import threading
import urllib.parse
import webbrowser
from collections.abc import Callable
from http import HTTPStatus
from typing import ClassVar
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import OAuth2Client
from authlib.oauth2.rfc6749 import OAuth2Error, OAuth2Token

from engagedin.core.config import settings

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_SCOPES = ["openid", "profile", "email", "w_member_social"]
REDIRECT_URI = "http://localhost:18473/callback"
CALLBACK_PORT = 18473


class OAuthError(Exception):
    """Raised when the OAuth 2.0 flow fails."""


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    authorization_code: ClassVar[str | None] = None
    expected_state: ClassVar[str] = ""

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        returned_state = params.get("state", [None])[0]
        code = params.get("code", [None])[0]

        if returned_state != self.expected_state:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.end_headers()
            self.wfile.write(b"State mismatch")
            return

        if code:
            OAuthCallbackHandler.authorization_code = code
            self.send_response(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(
                b"Authentication successful! You can close this tab."
            )
        else:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.end_headers()
            self.wfile.write(b"Authorization failed")


def build_authorization_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": " ".join(LINKEDIN_SCOPES),
    }
    return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(authorization_code: str) -> OAuth2Token:
    client = OAuth2Client(
        client_id=settings.linkedin_client_id,
        client_secret=settings.linkedin_client_secret,
    )
    token = client.fetch_token(
        LINKEDIN_TOKEN_URL,
        authorization_response=f"{REDIRECT_URI}?code={authorization_code}",
        grant_type="authorization_code",
    )
    return token


def get_user_urn(access_token: str) -> str:
    response = httpx.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    data = response.json()
    return f"urn:li:person:{data['sub']}"


def run_oauth_login(
    on_url: Callable[[str], None] | None = None,
) -> tuple[str, str]:
    """Run the OAuth 2.0 browser flow and return (access_token, user_urn)."""
    state = secrets.token_urlsafe(32)
    auth_url = build_authorization_url(state)
    if on_url is not None:
        on_url(auth_url)

    OAuthCallbackHandler.authorization_code = None
    OAuthCallbackHandler.expected_state = state

    server = http.server.HTTPServer(("localhost", CALLBACK_PORT), OAuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    webbrowser.open(auth_url)
    server.handle_request()
    server.server_close()

    code = OAuthCallbackHandler.authorization_code
    if not code:
        raise OAuthError("Authorization failed or was cancelled")

    try:
        token = exchange_code_for_token(code)
    except (httpx.HTTPError, OAuth2Error) as e:
        raise OAuthError(f"Failed to exchange the authorization code: {e}") from e
    access_token = token.get("access_token", "")
    if not access_token:
        raise OAuthError("Failed to obtain access token")

    try:
        user_urn = get_user_urn(access_token)
    except httpx.HTTPError as e:
        raise OAuthError(f"Failed to fetch your profile: {e}") from e
    return access_token, user_urn
