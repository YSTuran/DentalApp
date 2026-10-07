"""prevent conflicting active roles for one user

Revision ID: a8c3e5f0d6b4
Revises: f7b2d4e9c5a3
Create Date: 2026-10-07 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8c3e5f0d6b4"
down_revision: str | Sequence[str] | None = "f7b2d4e9c5a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid_user = connection.scalar(
        sa.text(
            """
            SELECT user_id
            FROM user_role_assignments
            WHERE is_active
            GROUP BY user_id
            HAVING count(DISTINCT role) > 1
            LIMIT 1
            """
        )
    )
    if invalid_user is not None:
        raise RuntimeError(
            "Migration öncesinde çakışan aktif rolleri bulunan kullanıcı "
            f"düzeltilmelidir: {invalid_user}"
        )

    op.execute(
        """
        CREATE FUNCTION enforce_user_single_active_role() RETURNS trigger AS $$
        BEGIN
            IF NEW.is_active AND EXISTS (
                SELECT 1
                FROM user_role_assignments AS existing
                WHERE existing.user_id = NEW.user_id
                  AND existing.id <> NEW.id
                  AND existing.is_active
                  AND existing.role::text <> NEW.role::text
            ) THEN
                RAISE EXCEPTION 'A user cannot have conflicting active roles'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_user_role_assignments_single_active_role';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_user_role_assignments_single_active_role
        BEFORE INSERT OR UPDATE OF user_id, role, is_active
        ON user_role_assignments
        FOR EACH ROW EXECUTE FUNCTION enforce_user_single_active_role();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_user_role_assignments_single_active_role
        ON user_role_assignments;
        DROP FUNCTION IF EXISTS enforce_user_single_active_role();
        """
    )
