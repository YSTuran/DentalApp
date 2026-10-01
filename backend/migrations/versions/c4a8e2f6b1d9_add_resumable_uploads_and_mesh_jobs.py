"""add resumable uploads and durable mesh validation state

Revision ID: c4a8e2f6b1d9
Revises: b1d4f7a9c2e5
Create Date: 2026-10-01 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4a8e2f6b1d9"
down_revision: str | Sequence[str] | None = "b1d4f7a9c2e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

case_file_kind_enum = postgresql.ENUM(
    "scan",
    "design",
    name="case_file_kind",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "case_file_versions",
        sa.Column(
            "mesh_validation_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "case_file_versions",
        sa.Column("mesh_validation_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "case_file_versions",
        sa.Column("mesh_validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_case_file_versions_mesh_validation_attempts_non_negative",
        "case_file_versions",
        "mesh_validation_attempts >= 0",
    )

    op.create_table(
        "case_upload_sessions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("kind", case_file_kind_enum, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("expected_size", sa.BigInteger(), nullable=False),
        sa.Column("received_size", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("expected_sha256", sa.String(length=64), nullable=True),
        sa.Column("temp_storage_key", sa.String(length=500), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "uploading",
                "completed",
                "failed",
                "expired",
                name="upload_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_reason", sa.String(length=100), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("completed_file_version_id", sa.Uuid(), nullable=True),
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
            "expected_size > 0",
            name="ck_case_upload_sessions_expected_size_positive",
        ),
        sa.CheckConstraint(
            "expected_sha256 IS NULL OR length(expected_sha256) = 64",
            name="ck_case_upload_sessions_expected_sha256_length",
        ),
        sa.CheckConstraint(
            "received_size >= 0",
            name="ck_case_upload_sessions_received_size_non_negative",
        ),
        sa.CheckConstraint(
            "received_size <= expected_size",
            name="ck_case_upload_sessions_received_size_not_excessive",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_case_upload_sessions_case_id_cases",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["completed_file_version_id"],
            ["case_file_versions.id"],
            name="fk_upload_completed_file_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_case_upload_sessions_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_case_upload_sessions"),
        sa.UniqueConstraint(
            "completed_file_version_id",
            name="uq_case_upload_sessions_completed_file_version_id",
        ),
        sa.UniqueConstraint(
            "temp_storage_key",
            name="uq_case_upload_sessions_temp_storage_key",
        ),
    )
    op.create_index(
        "ix_case_upload_sessions_case_id",
        "case_upload_sessions",
        ["case_id"],
    )
    op.create_index(
        "ix_case_upload_sessions_case_status",
        "case_upload_sessions",
        ["case_id", "status"],
    )
    op.create_index(
        "ix_case_upload_sessions_expires_at",
        "case_upload_sessions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_case_upload_sessions_expires_at", table_name="case_upload_sessions")
    op.drop_index("ix_case_upload_sessions_case_status", table_name="case_upload_sessions")
    op.drop_index("ix_case_upload_sessions_case_id", table_name="case_upload_sessions")
    op.drop_table("case_upload_sessions")

    op.drop_constraint(
        "ck_case_file_versions_mesh_validation_attempts_non_negative",
        "case_file_versions",
        type_="check",
    )
    op.drop_column("case_file_versions", "mesh_validated_at")
    op.drop_column("case_file_versions", "mesh_validation_started_at")
    op.drop_column("case_file_versions", "mesh_validation_attempts")
