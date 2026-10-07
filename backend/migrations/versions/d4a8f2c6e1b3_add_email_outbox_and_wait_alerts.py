"""add email outbox and case wait alerts

Revision ID: d4a8f2c6e1b3
Revises: c2e7a4f9b1d6
Create Date: 2026-10-06 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4a8f2c6e1b3"
down_revision: str | Sequence[str] | None = "c2e7a4f9b1d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

case_status_enum = postgresql.ENUM(
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
    name="case_status",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "email_outbox",
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
            "status IN ('pending', 'processing', 'retry', 'sent', 'failed')",
            name="ck_email_outbox_status_valid",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_email_outbox_attempt_count_non_negative",
        ),
        sa.CheckConstraint(
            "length(btrim(recipient_email)) > 0",
            name="ck_email_outbox_recipient_required",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name="fk_email_outbox_notification_id_notifications",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            name="fk_email_outbox_recipient_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_outbox"),
        sa.UniqueConstraint("notification_id", name="uq_email_outbox_notification_id"),
    )
    op.create_index(
        "ix_email_outbox_dispatch",
        "email_outbox",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_email_outbox_recipient_user_id",
        "email_outbox",
        ["recipient_user_id"],
    )

    op.create_table(
        "case_wait_alerts",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("case_status", case_status_enum, nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("stage_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("threshold_hours", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "threshold_hours > 0",
            name="ck_case_wait_alerts_threshold_hours_positive",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_case_wait_alerts_case_id_cases",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name="fk_case_wait_alerts_notification_id_notifications",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            name="fk_case_wait_alerts_recipient_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_case_wait_alerts"),
        sa.UniqueConstraint("notification_id", name="uq_case_wait_alerts_notification_id"),
        sa.UniqueConstraint(
            "case_id",
            "case_status",
            "recipient_user_id",
            "stage_started_at",
            name="uq_case_wait_alert_stage_recipient",
        ),
    )
    op.create_index(
        "ix_case_wait_alerts_case_id",
        "case_wait_alerts",
        ["case_id"],
    )
    op.create_index(
        "ix_case_wait_alerts_case_status",
        "case_wait_alerts",
        ["case_id", "case_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_case_wait_alerts_case_status", table_name="case_wait_alerts")
    op.drop_index("ix_case_wait_alerts_case_id", table_name="case_wait_alerts")
    op.drop_table("case_wait_alerts")
    op.drop_index("ix_email_outbox_recipient_user_id", table_name="email_outbox")
    op.drop_index("ix_email_outbox_dispatch", table_name="email_outbox")
    op.drop_table("email_outbox")
