"""add user notifications

Revision ID: c2e7a4f9b1d6
Revises: b9f1d4e6a8c2
Create Date: 2026-10-06 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2e7a4f9b1d6"
down_revision: str | Sequence[str] | None = "b9f1d4e6a8c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("case_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("target_path", sa.String(length=500), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("length(btrim(message)) > 0", name="ck_notifications_message_required"),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_notifications_title_required"),
        sa.CheckConstraint(
            "target_path IS NULL OR "
            "(left(target_path, 1) = '/' AND left(target_path, 2) <> '//')",
            name="ck_notifications_target_path_internal",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_notifications_actor_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_notifications_case_id_cases",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            name="fk_notifications_recipient_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index(
        "ix_notifications_case_id",
        "notifications",
        ["case_id"],
    )
    op.create_index(
        "ix_notifications_recipient_active_created",
        "notifications",
        ["recipient_user_id", "dismissed_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_active_created", table_name="notifications")
    op.drop_index("ix_notifications_case_id", table_name="notifications")
    op.drop_table("notifications")
