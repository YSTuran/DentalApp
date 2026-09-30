"""expand color palettes

Revision ID: e9a1c4f7b2d6
Revises: d8e0f3a5b7c9
Create Date: 2026-09-29 15:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e9a1c4f7b2d6"
down_revision: str | Sequence[str] | None = "d8e0f3a5b7c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_user_preferences_color_palette"
ORIGINAL_PALETTES = "'default', 'ocean', 'violet'"
EXPANDED_PALETTES = (
    f"{ORIGINAL_PALETTES}, 'arctic', 'sage', 'graphite', 'amber', "
    "'burgundy', 'coral', 'sepia', 'high_contrast'"
)


def upgrade() -> None:
    op.drop_constraint(op.f(CONSTRAINT_NAME), "user_preferences", type_="check")
    op.create_check_constraint(
        op.f(CONSTRAINT_NAME),
        "user_preferences",
        sa.text(f"color_palette IN ({EXPANDED_PALETTES})"),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE user_preferences SET color_palette = 'default' "
            f"WHERE color_palette NOT IN ({ORIGINAL_PALETTES})"
        )
    )
    op.drop_constraint(op.f(CONSTRAINT_NAME), "user_preferences", type_="check")
    op.create_check_constraint(
        op.f(CONSTRAINT_NAME),
        "user_preferences",
        sa.text(f"color_palette IN ({ORIGINAL_PALETTES})"),
    )
