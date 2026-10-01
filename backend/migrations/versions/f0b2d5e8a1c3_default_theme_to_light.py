"""default new users to the light theme

Revision ID: f0b2d5e8a1c3
Revises: e9a1c4f7b2d6
Create Date: 2026-09-30 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f0b2d5e8a1c3"
down_revision: str | Sequence[str] | None = "e9a1c4f7b2d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "user_preferences",
        "theme_mode",
        existing_type=sa.String(length=16),
        server_default="light",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user_preferences",
        "theme_mode",
        existing_type=sa.String(length=16),
        server_default="system",
        existing_nullable=False,
    )
