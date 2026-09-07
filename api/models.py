from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class PostStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    FAILED = "failed"


class DraftSource(StrEnum):
    STANDARD = "standard"
    HEADLINER = "headliner"


class PostRecord(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(500))
    source: Mapped[DraftSource] = mapped_column(
        Enum(DraftSource, native_enum=False, length=16)
    )
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, native_enum=False, length=16),
        default=PostStatus.DRAFT,
    )
    content: Mapped[str] = mapped_column(Text)
    character_count: Mapped[int]
    reference_url: Mapped[str | None] = mapped_column(String(2048))
    reference_title: Mapped[str | None] = mapped_column(String(1024))
    reference_description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(35))
    linkedin_post_urn: Mapped[str | None] = mapped_column(String(120), unique=True)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None]

    __table_args__ = (Index("ix_posts_status", "status"),)
