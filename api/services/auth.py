from __future__ import annotations

import asyncio

from api.exceptions import ExternalServiceError
from engagedin.linkedin.client import LinkedInClient, LinkedInError


class AuthService:
    async def get_status(self) -> dict[str, str]:
        try:
            client = LinkedInClient()
            info = await asyncio.to_thread(client.get_user_info)
        except LinkedInError as e:
            raise ExternalServiceError(str(e)) from e
        return {
            "name": info.get("name", "Unknown"),
            "sub": info.get("sub", "Unknown"),
        }
