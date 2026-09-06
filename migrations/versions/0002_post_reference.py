"""add post reference columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-06 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("reference_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "posts",
        sa.Column("reference_title", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "posts",
        sa.Column("reference_description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("posts", "reference_description")
    op.drop_column("posts", "reference_title")
    op.drop_column("posts", "reference_url")
