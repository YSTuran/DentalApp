"""harden fulfillment approval and rescan integrity

Revision ID: b9f1d4e6a8c2
Revises: a7e3c9d1f5b2
Create Date: 2026-10-05 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9f1d4e6a8c2"
down_revision: str | Sequence[str] | None = "a7e3c9d1f5b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS return_decisions_append_only ON return_decisions")
    op.add_column(
        "return_decisions",
        sa.Column("source_scan_file_version_id", sa.Uuid(), nullable=True),
    )
    op.execute(
        """
        UPDATE return_decisions AS decision
        SET source_scan_file_version_id = (
            SELECT file.id
            FROM return_receipts AS receipt
            JOIN shipments AS shipment ON shipment.id = receipt.shipment_id
            JOIN production_runs AS run ON run.id = shipment.production_run_id
            JOIN case_file_versions AS file ON file.case_id = run.case_id
            WHERE receipt.id = decision.return_receipt_id
              AND file.kind = 'scan'
            ORDER BY file.version_number DESC
            LIMIT 1
        )
        """
    )
    op.alter_column("return_decisions", "source_scan_file_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_return_decisions_source_scan_file_version_id_case_file_versions"),
        "return_decisions",
        "case_file_versions",
        ["source_scan_file_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        """
        CREATE TRIGGER return_decisions_append_only
        BEFORE UPDATE OR DELETE OR TRUNCATE ON return_decisions
        FOR EACH STATEMENT
        EXECUTE FUNCTION reject_fulfillment_mutation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_production_run_approvals()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM cases
                WHERE id = NEW.case_id
                  AND status IN ('ready_for_production', 'reproduction_requested')
            ) THEN
                RAISE EXCEPTION 'Vaka üretime hazır durumda olmalıdır'
                    USING ERRCODE = '23514';
            END IF;
            IF NOT EXISTS (
                SELECT 1
                FROM case_file_versions AS file
                JOIN case_approvals AS approval
                  ON approval.file_version_id = file.id
                 AND approval.case_id = file.case_id
                WHERE file.id = NEW.design_file_version_id
                  AND file.case_id = NEW.case_id
                  AND file.kind = 'design'
                  AND file.is_locked
                  AND approval.approval_type = 'dentist_design'
                  AND approval.decision = 'approved'
            ) THEN
                RAISE EXCEPTION 'Üretim için onaylı ve kilitli tasarım gereklidir'
                    USING ERRCODE = '23514';
            END IF;
            IF NOT EXISTS (
                SELECT 1
                FROM case_approvals
                WHERE case_id = NEW.case_id
                  AND approval_type = 'manager_scan'
                  AND decision = 'approved'
            ) THEN
                RAISE EXCEPTION 'Üretim için yönetici tarama onayı gereklidir'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER production_runs_validate_approvals
        BEFORE INSERT ON production_runs
        FOR EACH ROW
        EXECUTE FUNCTION validate_production_run_approvals()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS production_runs_validate_approvals ON production_runs")
    op.execute("DROP FUNCTION IF EXISTS validate_production_run_approvals()")
    op.drop_constraint(
        op.f("fk_return_decisions_source_scan_file_version_id_case_file_versions"),
        "return_decisions",
        type_="foreignkey",
    )
    op.drop_column("return_decisions", "source_scan_file_version_id")
