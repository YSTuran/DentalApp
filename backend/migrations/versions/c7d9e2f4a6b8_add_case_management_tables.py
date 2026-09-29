"""add case management tables

Revision ID: c7d9e2f4a6b8
Revises: f4b8c0a1d2e3
Create Date: 2026-09-29 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7d9e2f4a6b8"
down_revision: str | Sequence[str] | None = "f4b8c0a1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

case_status_values = (
    "draft",
    "manager_review",
    "manager_revision_requested",
    "manager_rejected",
    "lab_design",
    "dentist_review",
    "design_revision_requested",
    "ready_for_production",
    "in_production",
    "production_completed",
    "shipped",
    "delivered",
    "return_review",
    "reproduction_requested",
    "rescan_requested",
    "cancelled",
)

case_status_enum = postgresql.ENUM(*case_status_values, name="case_status", create_type=False)
case_file_kind_enum = postgresql.ENUM("scan", "design", name="case_file_kind", create_type=False)
mesh_validation_status_enum = postgresql.ENUM(
    "pending",
    "valid",
    "invalid",
    "failed",
    name="mesh_validation_status",
    create_type=False,
)
case_approval_type_enum = postgresql.ENUM(
    "manager_scan",
    "dentist_design",
    name="case_approval_type",
    create_type=False,
)
case_decision_enum = postgresql.ENUM(
    "approved",
    "revision_requested",
    "rejected",
    name="case_decision",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*case_status_values, name="case_status").create(bind, checkfirst=True)
    postgresql.ENUM("scan", "design", name="case_file_kind").create(bind, checkfirst=True)
    postgresql.ENUM(
        "pending",
        "valid",
        "invalid",
        "failed",
        name="mesh_validation_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "manager_scan",
        "dentist_design",
        name="case_approval_type",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "approved",
        "revision_requested",
        "rejected",
        name="case_decision",
    ).create(bind, checkfirst=True)
    op.execute("CREATE SEQUENCE case_number_seq START WITH 1 INCREMENT BY 1")

    op.create_table(
        "cases",
        sa.Column("case_number", sa.String(length=32), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("responsible_dentist_user_id", sa.Uuid(), nullable=False),
        sa.Column("patient_code", sa.String(length=100), nullable=True),
        sa.Column("patient_name", sa.String(length=200), nullable=True),
        sa.Column("status", case_status_enum, server_default="draft", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_cases_clinic_id_clinics"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_cases_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["responsible_dentist_user_id"],
            ["users.id"],
            name=op.f("fk_cases_responsible_dentist_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
    )
    op.create_index("ix_cases_clinic_id", "cases", ["clinic_id"])
    op.create_index("ix_cases_created_by_user_id", "cases", ["created_by_user_id"])
    op.create_index(
        "ix_cases_responsible_dentist_user_id",
        "cases",
        ["responsible_dentist_user_id"],
    )
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("uq_cases_case_number", "cases", ["case_number"], unique=True)
    op.create_index("ix_cases_clinic_status", "cases", ["clinic_id", "status"])
    op.create_index("ix_cases_created_at", "cases", ["created_at"])

    op.create_table(
        "case_details",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("appliance_type", sa.String(length=100), nullable=True),
        sa.Column("material", sa.String(length=100), nullable=True),
        sa.Column(
            "tooth_numbers",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("special_notes", sa.Text(), nullable=True),
        sa.Column(
            "extra_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
            "jsonb_typeof(tooth_numbers) = 'array'",
            name=op.f("ck_case_details_tooth_numbers_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(extra_fields) = 'object'",
            name=op.f("ck_case_details_extra_fields_object"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_case_details_case_id_cases"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("case_id", name=op.f("pk_case_details")),
    )

    op.create_table(
        "case_file_versions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("kind", case_file_kind_enum, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "mesh_status",
            mesh_validation_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("mesh_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.CheckConstraint(
            "version_number > 0",
            name=op.f("ck_case_file_versions_version_number_positive"),
        ),
        sa.CheckConstraint(
            "size_bytes > 0",
            name=op.f("ck_case_file_versions_size_bytes_positive"),
        ),
        sa.CheckConstraint(
            "length(sha256) = 64",
            name=op.f("ck_case_file_versions_sha256_length"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_case_file_versions_case_id_cases"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_case_file_versions_uploaded_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_file_versions")),
        sa.UniqueConstraint(
            "case_id",
            "kind",
            "version_number",
            name="uq_case_file_version_number",
        ),
        sa.UniqueConstraint("storage_key", name="uq_case_file_versions_storage_key"),
    )
    op.create_index("ix_case_file_versions_case_id", "case_file_versions", ["case_id"])
    op.create_index(
        "ix_case_file_versions_case_kind",
        "case_file_versions",
        ["case_id", "kind"],
    )

    op.create_table(
        "case_approvals",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("approval_type", case_approval_type_enum, nullable=False),
        sa.Column("decision", case_decision_enum, nullable=False),
        sa.Column("file_version_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "is_self_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_case_approvals_actor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_case_approvals_case_id_cases"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["file_version_id"],
            ["case_file_versions.id"],
            name=op.f("fk_case_approvals_file_version_id_case_file_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_approvals")),
    )
    op.create_index("ix_case_approvals_case_id", "case_approvals", ["case_id"])
    op.create_index(
        "ix_case_approvals_case_created",
        "case_approvals",
        ["case_id", "created_at"],
    )

    op.create_table(
        "case_status_history",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", case_status_enum, nullable=True),
        sa.Column("to_status", case_status_enum, nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_case_status_history_actor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_case_status_history_case_id_cases"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_status_history")),
    )
    op.create_index("ix_case_status_history_case_id", "case_status_history", ["case_id"])
    op.create_index(
        "ix_case_status_history_case_created",
        "case_status_history",
        ["case_id", "created_at"],
    )

    op.execute(
        """
        CREATE FUNCTION reject_case_append_only_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'Onay ve vaka geçmişi kayıtları değiştirilemez veya silinemez'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    for table_name in ("case_approvals", "case_status_history"):
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_append_only
            BEFORE UPDATE OR DELETE OR TRUNCATE ON {table_name}
            FOR EACH STATEMENT
            EXECUTE FUNCTION reject_case_append_only_mutation()
            """
        )

    op.execute(
        """
        CREATE FUNCTION reject_case_record_deletion()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'Vaka kayıtları silinemez'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    for table_name in ("cases", "case_details", "case_file_versions"):
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_no_delete
            BEFORE DELETE OR TRUNCATE ON {table_name}
            FOR EACH STATEMENT
            EXECUTE FUNCTION reject_case_record_deletion()
            """
        )


def downgrade() -> None:
    for table_name in ("cases", "case_details", "case_file_versions"):
        op.execute(f"DROP TRIGGER IF EXISTS {table_name}_no_delete ON {table_name}")
    op.execute("DROP FUNCTION IF EXISTS reject_case_record_deletion()")
    for table_name in ("case_approvals", "case_status_history"):
        op.execute(f"DROP TRIGGER IF EXISTS {table_name}_append_only ON {table_name}")
    op.execute("DROP FUNCTION IF EXISTS reject_case_append_only_mutation()")

    op.drop_table("case_status_history")
    op.drop_table("case_approvals")
    op.drop_table("case_file_versions")
    op.drop_table("case_details")
    op.drop_table("cases")
    op.execute("DROP SEQUENCE IF EXISTS case_number_seq")

    case_decision_enum.drop(op.get_bind(), checkfirst=True)
    case_approval_type_enum.drop(op.get_bind(), checkfirst=True)
    mesh_validation_status_enum.drop(op.get_bind(), checkfirst=True)
    case_file_kind_enum.drop(op.get_bind(), checkfirst=True)
    case_status_enum.drop(op.get_bind(), checkfirst=True)
