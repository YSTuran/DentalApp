"""separate user roles from clinic assignments

Revision ID: c0e5a7b2f8d1
Revises: b9d4f6a1e7c5
Create Date: 2026-10-07 14:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c0e5a7b2f8d1"
down_revision: str | Sequence[str] | None = "b9d4f6a1e7c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_clinic_assignments",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name=op.f("fk_user_clinic_assignments_clinic_id_clinics"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_clinic_assignments_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_clinic_assignments")),
        sa.UniqueConstraint(
            "user_id",
            "clinic_id",
            name=op.f("uq_user_clinic_assignments_user_clinic"),
        ),
    )
    op.create_index(
        op.f("ix_user_clinic_assignments_user_id"),
        "user_clinic_assignments",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_user_clinic_assignments_clinic_id"),
        "user_clinic_assignments",
        ["clinic_id"],
    )
    op.create_index(
        "ix_user_clinic_assignments_clinic_active",
        "user_clinic_assignments",
        ["clinic_id", "is_active"],
    )

    op.execute(
        """
        INSERT INTO user_clinic_assignments (
            id, user_id, clinic_id, is_active, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            user_id,
            clinic_id,
            bool_or(is_active),
            min(created_at),
            max(updated_at)
        FROM user_role_assignments
        WHERE clinic_id IS NOT NULL
        GROUP BY user_id, clinic_id
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY user_id
                       ORDER BY is_active DESC, updated_at DESC, created_at DESC, id
                   ) AS position
            FROM user_role_assignments
        )
        UPDATE user_role_assignments AS assignment
        SET is_active = false
        FROM ranked
        WHERE assignment.id = ranked.id
          AND ranked.position > 1
          AND assignment.is_active
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_user_role_assignments_multi_clinic
        ON user_role_assignments;
        DROP FUNCTION IF EXISTS enforce_user_multi_clinic_role();
        DROP TRIGGER IF EXISTS trg_user_role_assignments_single_active_role
        ON user_role_assignments;
        DROP FUNCTION IF EXISTS enforce_user_single_active_role();
        """
    )
    op.drop_index("uq_user_role_assignment_clinic", table_name="user_role_assignments")
    op.drop_index("uq_user_role_assignment_global", table_name="user_role_assignments")
    op.drop_index("ix_user_role_assignments_clinic_role", table_name="user_role_assignments")
    op.drop_constraint(
        op.f("ck_user_role_assignments_role_scope"),
        "user_role_assignments",
        type_="check",
    )
    op.execute("UPDATE user_role_assignments SET clinic_id = NULL")
    op.create_check_constraint(
        "role_has_no_clinic",
        "user_role_assignments",
        "clinic_id IS NULL",
    )
    op.create_index(
        "ix_user_role_assignments_role_active",
        "user_role_assignments",
        ["role", "is_active"],
    )
    op.create_index(
        "uq_user_role_assignment_active_user",
        "user_role_assignments",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_user_role_assignment_active_user",
        table_name="user_role_assignments",
        postgresql_where=sa.text("is_active"),
    )
    op.drop_index("ix_user_role_assignments_role_active", table_name="user_role_assignments")
    op.drop_constraint(
        op.f("ck_user_role_assignments_role_has_no_clinic"),
        "user_role_assignments",
        type_="check",
    )
    op.execute(
        """
        UPDATE user_role_assignments AS role_assignment
        SET clinic_id = clinic_assignment.clinic_id
        FROM (
            SELECT DISTINCT ON (user_id) user_id, clinic_id
            FROM user_clinic_assignments
            WHERE is_active
            ORDER BY user_id, created_at, id
        ) AS clinic_assignment
        WHERE role_assignment.user_id = clinic_assignment.user_id
          AND role_assignment.role::text NOT IN ('system_admin', 'technician')
        """
    )
    op.create_check_constraint(
        "role_scope",
        "user_role_assignments",
        "(role IN ('system_admin', 'technician') AND clinic_id IS NULL) OR "
        "(role IN ('clinic_manager', 'managing_dentist', 'dentist', 'clinic_staff') "
        "AND clinic_id IS NOT NULL)",
    )
    op.create_index(
        "uq_user_role_assignment_global",
        "user_role_assignments",
        ["user_id", "role"],
        unique=True,
        postgresql_where=sa.text("clinic_id IS NULL"),
    )
    op.create_index(
        "uq_user_role_assignment_clinic",
        "user_role_assignments",
        ["user_id", "role", "clinic_id"],
        unique=True,
        postgresql_where=sa.text("clinic_id IS NOT NULL"),
    )
    op.create_index(
        "ix_user_role_assignments_clinic_role",
        "user_role_assignments",
        ["clinic_id", "role"],
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
    op.drop_index(
        "ix_user_clinic_assignments_clinic_active",
        table_name="user_clinic_assignments",
    )
    op.drop_index(
        op.f("ix_user_clinic_assignments_clinic_id"),
        table_name="user_clinic_assignments",
    )
    op.drop_index(
        op.f("ix_user_clinic_assignments_user_id"),
        table_name="user_clinic_assignments",
    )
    op.drop_table("user_clinic_assignments")
