"""create posts table

Revision ID: 0001
Revises:
Create Date: 2026-09-04 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic", sa.String(length=500), nullable=False),
        sa.Column(
            "source",
            sa.Enum("standard", "headliner", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "failed", native_enum=False, length=16),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column(
            "linkedin_post_urn", sa.String(length=120), nullable=True, unique=True
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("published_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_posts_status", "posts", ["status"])
    op.create_index("ix_posts_created_at", "posts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_posts_created_at")
    op.drop_index("ix_posts_status")
    op.drop_table("posts")
