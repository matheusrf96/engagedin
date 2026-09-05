from __future__ import annotations


class ExternalServiceError(Exception):
    """Raised when an external call (LLM, LinkedIn, news) fails."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code
