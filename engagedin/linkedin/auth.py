from __future__ import annotations

import http.server
import urllib.parse
from typing import ClassVar
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import OAuth2Client
from authlib.oauth2.rfc6749 import OAuth2Token

from engagedin.core.config import settings

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_SCOPES = ["openid", "profile", "email", "w_member_social"]
REDIRECT_URI = "http://localhost:18473/callback"


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    authorization_code: ClassVar[str | None] = None
    expected_state: ClassVar[str] = ""

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        returned_state = params.get("state", [None])[0]
        code = params.get("code", [None])[0]

        if returned_state != self.expected_state:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch")
            return

        if code:
            OAuthCallbackHandler.authorization_code = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"Authentication successful! You can close this tab."
            )
        else:
            self.send_response(400)
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
