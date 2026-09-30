"""add user theme preferences

Revision ID: d8e0f3a5b7c9
Revises: c7d9e2f4a6b8
Create Date: 2026-09-29 13:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8e0f3a5b7c9"
down_revision: str | Sequence[str] | None = "c7d9e2f4a6b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "theme_mode",
            sa.String(length=16),
            server_default="system",
            nullable=False,
        ),
        sa.Column(
            "color_palette",
            sa.String(length=32),
            server_default="default",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "theme_mode IN ('light', 'dark', 'system')",
            name=op.f("ck_user_preferences_theme_mode"),
        ),
        sa.CheckConstraint(
            "color_palette IN ('default', 'ocean', 'violet')",
            name=op.f("ck_user_preferences_color_palette"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_preferences_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_preferences")),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
