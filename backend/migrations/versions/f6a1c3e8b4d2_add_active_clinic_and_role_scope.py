"""add active clinic preference and restrict multi-clinic roles

Revision ID: f6a1c3e8b4d2
Revises: e5c7a9d2f4b6
Create Date: 2026-10-07 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a1c3e8b4d2"
down_revision: str | Sequence[str] | None = "e5c7a9d2f4b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid_user = connection.scalar(
        sa.text(
            """
            SELECT user_id
            FROM user_role_assignments
            WHERE is_active AND clinic_id IS NOT NULL
            GROUP BY user_id
            HAVING count(DISTINCT clinic_id) > 1
               AND bool_or(role::text <> 'clinic_manager')
            LIMIT 1
            """
        )
    )
    if invalid_user is not None:
        raise RuntimeError(
            "Migration öncesinde birden fazla klinikte klinik yöneticisi dışı rolü "
            f"bulunan kullanıcı düzeltmelidir: {invalid_user}"
        )

    op.add_column(
        "user_preferences",
        sa.Column("active_clinic_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_preferences_active_clinic",
        "user_preferences",
        "clinics",
        ["active_clinic_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        """
        CREATE FUNCTION enforce_user_multi_clinic_role() RETURNS trigger AS $$
        BEGIN
            IF NEW.is_active AND NEW.clinic_id IS NOT NULL AND EXISTS (
                SELECT 1
                FROM user_role_assignments AS existing
                WHERE existing.user_id = NEW.user_id
                  AND existing.id <> NEW.id
                  AND existing.is_active
                  AND existing.clinic_id IS NOT NULL
                  AND existing.clinic_id <> NEW.clinic_id
                  AND (
                      existing.role::text <> 'clinic_manager'
                      OR NEW.role::text <> 'clinic_manager'
                  )
            ) THEN
                RAISE EXCEPTION 'Only clinic managers may have assignments in multiple clinics'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_user_role_assignments_multi_clinic';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_user_role_assignments_multi_clinic
        BEFORE INSERT OR UPDATE OF user_id, role, clinic_id, is_active
        ON user_role_assignments
        FOR EACH ROW EXECUTE FUNCTION enforce_user_multi_clinic_role();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_user_role_assignments_multi_clinic
        ON user_role_assignments;
        DROP FUNCTION IF EXISTS enforce_user_multi_clinic_role();
        """
    )
    op.drop_constraint(
        "fk_user_preferences_active_clinic",
        "user_preferences",
        type_="foreignkey",
    )
    op.drop_column("user_preferences", "active_clinic_id")
