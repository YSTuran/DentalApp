"""add immutable case transfer workflow

Revision ID: f7b2d4e9c5a3
Revises: f6a1c3e8b4d2
Create Date: 2026-10-07 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7b2d4e9c5a3"
down_revision: str | Sequence[str] | None = "f6a1c3e8b4d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_transfers",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("from_dentist_user_id", sa.Uuid(), nullable=False),
        sa.Column("to_dentist_user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "accepted",
                "rejected",
                name="case_transfer_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("request_reason", sa.Text(), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "from_dentist_user_id <> to_dentist_user_id",
            name=op.f("ck_case_transfers_different_dentists"),
        ),
        sa.CheckConstraint(
            "length(btrim(request_reason)) >= 3",
            name=op.f("ck_case_transfers_request_reason_required"),
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND decided_by_user_id IS NULL AND decided_at IS NULL "
            "AND decision_reason IS NULL) OR "
            "(status IN ('accepted', 'rejected') AND decided_by_user_id IS NOT NULL "
            "AND decided_at IS NOT NULL)",
            name=op.f("ck_case_transfers_decision_state"),
        ),
        sa.CheckConstraint(
            "status <> 'rejected' OR length(btrim(decision_reason)) >= 3",
            name=op.f("ck_case_transfers_rejection_reason_required"),
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["from_dentist_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_dentist_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_transfers")),
    )
    op.create_index(op.f("ix_case_transfers_case_id"), "case_transfers", ["case_id"])
    op.create_index(
        "ix_case_transfers_target_status",
        "case_transfers",
        ["to_dentist_user_id", "status"],
    )
    op.create_index(
        "uq_case_transfers_pending_case",
        "case_transfers",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.execute(
        """
        CREATE FUNCTION protect_case_transfers() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'case transfer records cannot be deleted';
            END IF;
            IF OLD.status <> 'pending' THEN
                RAISE EXCEPTION 'decided case transfer records are immutable';
            END IF;
            IF NEW.status NOT IN ('accepted', 'rejected')
               OR NEW.case_id <> OLD.case_id
               OR NEW.from_dentist_user_id <> OLD.from_dentist_user_id
               OR NEW.to_dentist_user_id <> OLD.to_dentist_user_id
               OR NEW.requested_by_user_id <> OLD.requested_by_user_id
               OR NEW.request_reason <> OLD.request_reason
               OR NEW.requested_at <> OLD.requested_at THEN
                RAISE EXCEPTION 'invalid case transfer mutation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_case_transfers_protect_row
        BEFORE UPDATE OR DELETE ON case_transfers
        FOR EACH ROW EXECUTE FUNCTION protect_case_transfers();

        CREATE FUNCTION prevent_case_transfers_truncate() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'case transfer records cannot be truncated';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_case_transfers_prevent_truncate
        BEFORE TRUNCATE ON case_transfers
        FOR EACH STATEMENT EXECUTE FUNCTION prevent_case_transfers_truncate();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_case_transfers_prevent_truncate ON case_transfers;
        DROP FUNCTION IF EXISTS prevent_case_transfers_truncate();
        DROP TRIGGER IF EXISTS trg_case_transfers_protect_row ON case_transfers;
        DROP FUNCTION IF EXISTS protect_case_transfers();
        """
    )
    op.drop_index("uq_case_transfers_pending_case", table_name="case_transfers")
    op.drop_index("ix_case_transfers_target_status", table_name="case_transfers")
    op.drop_index(op.f("ix_case_transfers_case_id"), table_name="case_transfers")
    op.drop_table("case_transfers")
