from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from api.models import DraftSource, PostStatus


class DraftCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    source: Literal["standard", "headliner"] = "standard"
    days: int = Field(default=1, ge=1, le=7)
    language: str | None = None


class PostUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=3000)


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    source: DraftSource
    status: PostStatus
    content: str
    character_count: int
    reference_url: str | None
    reference_title: str | None
    reference_description: str | None
    language: str | None
    linkedin_post_urn: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class PostListResponse(BaseModel):
    items: list[PostOut]
    total: int


class AuthStatusResponse(BaseModel):
    name: str
    sub: str
