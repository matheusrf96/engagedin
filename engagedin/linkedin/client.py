from __future__ import annotations

from http import HTTPStatus

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from engagedin.core.config import settings
from engagedin.core.models import Post

API_BASE = "https://api.linkedin.com"
POSTS_ENDPOINT = "/rest/posts"
LINKEDIN_VERSION = "202506"

# GETs are idempotent, so any transport error is safe to retry.
RETRYABLE_ERRORS = httpx.TransportError
# create_post is a non-idempotent POST: retrying mid-response errors
# (ReadTimeout, ReadError, WriteTimeout) could publish the same post twice.
# Only connection failures that occur before the request is sent are retried.
RETRYABLE_POST_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout)


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

    @retry(
        retry=retry_if_exception_type(RETRYABLE_POST_ERRORS),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _send_create_post(self, body: dict[str, object]) -> httpx.Response:
        return httpx.post(
            f"{API_BASE}{POSTS_ENDPOINT}",
            headers=self._headers(),
            json=body,
        )

    @retry(
        retry=retry_if_exception_type(RETRYABLE_ERRORS),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _send_userinfo_request(self) -> httpx.Response:
        return httpx.get(
            f"{API_BASE}/v2/userinfo",
            headers=self._headers(),
        )

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
        try:
            response = self._send_create_post(body)
        except httpx.HTTPError as e:
            raise LinkedInError(f"LinkedIn API error: {e}") from e
        if response.status_code != HTTPStatus.CREATED:
            raise LinkedInError(
                f"LinkedIn API error (HTTP {response.status_code}): {response.text}"
            )
        post_urn = response.headers.get("x-restli-id", "")
        if not post_urn:
            raise LinkedInError("No post URN returned by LinkedIn API")
        return post_urn

    def get_user_info(self) -> dict:
        try:
            response = self._send_userinfo_request()
        except httpx.HTTPError as e:
            raise LinkedInError(f"LinkedIn API error: {e}") from e
        try:
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise LinkedInError(f"LinkedIn API error (HTTP {response.status_code}): {e}") from e
        return response.json()
