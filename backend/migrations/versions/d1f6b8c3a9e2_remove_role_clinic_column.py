"""remove the legacy clinic column from role assignments

Revision ID: d1f6b8c3a9e2
Revises: c0e5a7b2f8d1
Create Date: 2026-10-07 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1f6b8c3a9e2"
down_revision: str | Sequence[str] | None = "c0e5a7b2f8d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_user_role_assignments_role_has_no_clinic"),
        "user_role_assignments",
        type_="check",
    )
    op.drop_index(
        op.f("ix_user_role_assignments_clinic_id"),
        table_name="user_role_assignments",
    )
    op.drop_constraint(
        op.f("fk_user_role_assignments_clinic_id_clinics"),
        "user_role_assignments",
        type_="foreignkey",
    )
    op.drop_column("user_role_assignments", "clinic_id")


def downgrade() -> None:
    op.add_column(
        "user_role_assignments",
        sa.Column("clinic_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_user_role_assignments_clinic_id_clinics"),
        "user_role_assignments",
        "clinics",
        ["clinic_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_user_role_assignments_clinic_id"),
        "user_role_assignments",
        ["clinic_id"],
    )
    op.create_check_constraint(
        "role_has_no_clinic",
        "user_role_assignments",
        "clinic_id IS NULL",
    )
