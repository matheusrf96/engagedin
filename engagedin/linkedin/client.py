from __future__ import annotations

import httpx

from engagedin.core.config import settings
from engagedin.core.models import Post

API_BASE = "https://api.linkedin.com"
POSTS_ENDPOINT = "/rest/posts"
LINKEDIN_VERSION = "202506"


class LinkedInError(Exception):
    pass


class LinkedInClient:
    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or settings.linkedin_access_token
        if not self.access_token:
            raise LinkedInError(
                "No LinkedIn access token available. "
                "Run `engagedin auth login` or set LINKEDIN_ACCESS_TOKEN in .env"
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": LINKEDIN_VERSION,
            "Content-Type": "application/json",
        }

    def create_post(self, post: Post) -> str:
        body = {
            "author": post.author,
            "commentary": post.commentary,
            "visibility": post.visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": post.lifecycle_state,
            "isReshareDisabledByAuthor": False,
        }
        response = httpx.post(
            f"{API_BASE}{POSTS_ENDPOINT}",
            headers=self._headers(),
            json=body,
        )
        if response.status_code != 201:
            raise LinkedInError(
                f"LinkedIn API error (HTTP {response.status_code}): {response.text}"
            )
        post_urn = response.headers.get("x-restli-id", "")
        if not post_urn:
            raise LinkedInError("No post URN returned by LinkedIn API")
        return post_urn

    def get_user_info(self) -> dict:
        response = httpx.get(
            f"{API_BASE}/v2/userinfo",
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()
