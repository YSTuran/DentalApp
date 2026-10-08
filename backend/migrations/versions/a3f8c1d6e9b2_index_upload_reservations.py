"""index active upload reservation lookups

Revision ID: a3f8c1d6e9b2
Revises: e2a7c5d9f1b4
Create Date: 2026-10-08 12:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a3f8c1d6e9b2"
down_revision: str | Sequence[str] | None = "e2a7c5d9f1b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_case_upload_sessions_creator_status_expiry",
        "case_upload_sessions",
        ["created_by_user_id", "status", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_case_upload_sessions_creator_status_expiry",
        table_name="case_upload_sessions",
    )
