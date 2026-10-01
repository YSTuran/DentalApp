"""harden workflow integrity and event ordering

Revision ID: b1d4f7a9c2e5
Revises: f0b2d5e8a1c3
Create Date: 2026-10-01 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1d4f7a9c2e5"
down_revision: str | Sequence[str] | None = "f0b2d5e8a1c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_sequence_number(table_name: str, index_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column(
            "sequence_number",
            sa.BigInteger(),
            sa.Identity(),
            nullable=False,
        ),
    )
    op.create_index(index_name, table_name, ["sequence_number"], unique=True)


def upgrade() -> None:
    _add_sequence_number("audit_events", "uq_audit_events_sequence_number")
    _add_sequence_number("case_approvals", "uq_case_approvals_sequence_number")
    _add_sequence_number("case_status_history", "uq_case_status_history_sequence_number")

    op.create_unique_constraint(
        "uq_case_file_versions_id_case",
        "case_file_versions",
        ["id", "case_id"],
    )
    op.drop_constraint(
        op.f("fk_case_approvals_file_version_id_case_file_versions"),
        "case_approvals",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_case_approvals_file_version_case",
        "case_approvals",
        "case_file_versions",
        ["file_version_id", "case_id"],
        ["id", "case_id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_case_approval_file_decision",
        "case_approvals",
        ["case_id", "approval_type", "file_version_id"],
    )
    op.create_check_constraint(
        "ck_case_approvals_decision_reason_required",
        "case_approvals",
        sa.text(
            "decision = 'approved' OR "
            "(reason IS NOT NULL AND length(btrim(reason)) >= 3)"
        ),
    )
    op.create_check_constraint(
        "ck_case_approvals_self_approval_manager_only",
        "case_approvals",
        sa.text("NOT is_self_approval OR approval_type = 'manager_scan'"),
    )

    op.execute(
        """
        CREATE FUNCTION validate_case_approval_artifact()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            artifact_kind case_file_kind;
        BEGIN
            SELECT kind INTO artifact_kind
            FROM case_file_versions
            WHERE id = NEW.file_version_id AND case_id = NEW.case_id;

            IF artifact_kind IS NULL THEN
                RAISE EXCEPTION 'Onay dosyası aynı vakaya ait olmalıdır'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.approval_type = 'manager_scan' AND artifact_kind <> 'scan' THEN
                RAISE EXCEPTION 'Yönetici onayı yalnızca tarama sürümüne bağlanabilir'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.approval_type = 'dentist_design' AND artifact_kind <> 'design' THEN
                RAISE EXCEPTION 'Hekim onayı yalnızca tasarım sürümüne bağlanabilir'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER case_approvals_validate_artifact
        BEFORE INSERT ON case_approvals
        FOR EACH ROW
        EXECUTE FUNCTION validate_case_approval_artifact()
        """
    )

    op.execute(
        """
        CREATE FUNCTION reject_locked_case_file_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.is_locked THEN
                RAISE EXCEPTION 'Kilitli vaka dosyası değiştirilemez'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER case_file_versions_locked_immutable
        BEFORE UPDATE ON case_file_versions
        FOR EACH ROW
        EXECUTE FUNCTION reject_locked_case_file_update()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS case_file_versions_locked_immutable ON case_file_versions"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_locked_case_file_update()")
    op.execute("DROP TRIGGER IF EXISTS case_approvals_validate_artifact ON case_approvals")
    op.execute("DROP FUNCTION IF EXISTS validate_case_approval_artifact()")

    op.drop_constraint(
        "ck_case_approvals_self_approval_manager_only",
        "case_approvals",
        type_="check",
    )
    op.drop_constraint(
        "ck_case_approvals_decision_reason_required",
        "case_approvals",
        type_="check",
    )
    op.drop_constraint(
        "uq_case_approval_file_decision",
        "case_approvals",
        type_="unique",
    )
    op.drop_constraint(
        "fk_case_approvals_file_version_case",
        "case_approvals",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_case_approvals_file_version_id_case_file_versions"),
        "case_approvals",
        "case_file_versions",
        ["file_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "uq_case_file_versions_id_case",
        "case_file_versions",
        type_="unique",
    )

    for table_name, index_name in (
        ("case_status_history", "uq_case_status_history_sequence_number"),
        ("case_approvals", "uq_case_approvals_sequence_number"),
        ("audit_events", "uq_audit_events_sequence_number"),
    ):
        op.drop_index(index_name, table_name=table_name)
        op.drop_column(table_name, "sequence_number")
