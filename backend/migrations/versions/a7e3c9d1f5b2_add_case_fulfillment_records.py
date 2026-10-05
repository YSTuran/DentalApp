"""add immutable production, delivery and return records

Revision ID: a7e3c9d1f5b2
Revises: c4a8e2f6b1d9
Create Date: 2026-10-05 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7e3c9d1f5b2"
down_revision: str | Sequence[str] | None = "c4a8e2f6b1d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

return_reason_enum = postgresql.ENUM(
    "fit_issue",
    "damaged",
    "manufacturing_defect",
    "other",
    name="return_reason_code",
    create_type=False,
)
return_resolution_enum = postgresql.ENUM(
    "reproduction",
    "rescan",
    name="return_resolution",
    create_type=False,
)

IMMUTABLE_TABLES = (
    "production_runs",
    "production_completions",
    "shipments",
    "delivery_confirmations",
    "return_receipts",
    "return_decisions",
)


def _id_and_time(column_name: str) -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            column_name,
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def _user_fk(column_name: str, table_name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column_name],
        ["users.id"],
        name=op.f(f"fk_{table_name}_{column_name}_users"),
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    return_reason_enum.create(op.get_bind(), checkfirst=True)
    return_resolution_enum.create(op.get_bind(), checkfirst=True)
    op.execute("CREATE SEQUENCE production_work_order_seq START WITH 1")

    op.create_table(
        "production_runs",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("design_file_version_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_number", sa.String(length=32), nullable=False),
        sa.Column("started_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_id_and_time("started_at"),
        sa.CheckConstraint(
            "attempt_number > 0", name=op.f("ck_production_runs_attempt_number_positive")
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_production_runs_case_id_cases"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["design_file_version_id", "case_id"],
            ["case_file_versions.id", "case_file_versions.case_id"],
            name="fk_production_run_design_case",
            ondelete="RESTRICT",
        ),
        _user_fk("started_by_user_id", "production_runs"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_production_runs")),
        sa.UniqueConstraint("id", "case_id", name="uq_production_runs_id_case"),
        sa.UniqueConstraint("case_id", "attempt_number", name="uq_production_run_attempt"),
        sa.UniqueConstraint("work_order_number", name="uq_production_run_work_order"),
    )
    op.create_index("ix_production_runs_case_id", "production_runs", ["case_id"])
    op.create_index(
        "ix_production_runs_case_started", "production_runs", ["case_id", "started_at"]
    )

    op.create_table(
        "production_completions",
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("material", sa.String(length=200), nullable=False),
        sa.Column("lot_number", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("completed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_id_and_time("completed_at"),
        sa.CheckConstraint(
            "length(btrim(material)) > 0",
            name=op.f("ck_production_completions_material_required"),
        ),
        sa.CheckConstraint(
            "length(btrim(lot_number)) > 0",
            name=op.f("ck_production_completions_lot_number_required"),
        ),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_production_completions_quantity_positive")
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name=op.f("fk_production_completions_production_run_id_production_runs"),
            ondelete="RESTRICT",
        ),
        _user_fk("completed_by_user_id", "production_completions"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_production_completions")),
        sa.UniqueConstraint(
            "production_run_id", name=op.f("uq_production_completions_production_run_id")
        ),
    )

    op.create_table(
        "shipments",
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("destination_clinic_id", sa.Uuid(), nullable=False),
        sa.Column("carrier", sa.String(length=120), nullable=False),
        sa.Column("tracking_number", sa.String(length=120), nullable=False),
        sa.Column("shipped_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_id_and_time("shipped_at"),
        sa.CheckConstraint(
            "length(btrim(carrier)) > 0", name=op.f("ck_shipments_carrier_required")
        ),
        sa.CheckConstraint(
            "length(btrim(tracking_number)) > 0",
            name=op.f("ck_shipments_tracking_number_required"),
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name=op.f("fk_shipments_production_run_id_production_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_clinic_id"],
            ["clinics.id"],
            name=op.f("fk_shipments_destination_clinic_id_clinics"),
            ondelete="RESTRICT",
        ),
        _user_fk("shipped_by_user_id", "shipments"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shipments")),
        sa.UniqueConstraint(
            "production_run_id", name=op.f("uq_shipments_production_run_id")
        ),
        sa.UniqueConstraint("carrier", "tracking_number", name="uq_shipment_carrier_tracking"),
    )
    op.create_index("ix_shipments_destination_clinic_id", "shipments", ["destination_clinic_id"])
    op.create_index(
        "ix_shipments_destination_shipped",
        "shipments",
        ["destination_clinic_id", "shipped_at"],
    )

    op.create_table(
        "delivery_confirmations",
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("received_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_id_and_time("delivered_at"),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name=op.f("fk_delivery_confirmations_shipment_id_shipments"),
            ondelete="RESTRICT",
        ),
        _user_fk("received_by_user_id", "delivery_confirmations"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delivery_confirmations")),
        sa.UniqueConstraint(
            "shipment_id", name=op.f("uq_delivery_confirmations_shipment_id")
        ),
    )

    op.create_table(
        "return_receipts",
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("reason_code", return_reason_enum, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("inspection_notes", sa.Text(), nullable=True),
        sa.Column("received_by_user_id", sa.Uuid(), nullable=False),
        *_id_and_time("received_at"),
        sa.CheckConstraint(
            "length(btrim(reason)) >= 3",
            name=op.f("ck_return_receipts_return_reason_required"),
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name=op.f("fk_return_receipts_shipment_id_shipments"),
            ondelete="RESTRICT",
        ),
        _user_fk("received_by_user_id", "return_receipts"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_return_receipts")),
        sa.UniqueConstraint("shipment_id", name=op.f("uq_return_receipts_shipment_id")),
    )

    op.create_table(
        "return_decisions",
        sa.Column("return_receipt_id", sa.Uuid(), nullable=False),
        sa.Column("resolution", return_resolution_enum, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=False),
        *_id_and_time("decided_at"),
        sa.CheckConstraint(
            "length(btrim(reason)) >= 3",
            name=op.f("ck_return_decisions_return_decision_reason_required"),
        ),
        sa.ForeignKeyConstraint(
            ["return_receipt_id"],
            ["return_receipts.id"],
            name=op.f("fk_return_decisions_return_receipt_id_return_receipts"),
            ondelete="RESTRICT",
        ),
        _user_fk("decided_by_user_id", "return_decisions"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_return_decisions")),
        sa.UniqueConstraint(
            "return_receipt_id", name=op.f("uq_return_decisions_return_receipt_id")
        ),
    )

    op.execute(
        """
        CREATE FUNCTION reject_fulfillment_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'Üretim, teslim ve iade kayıtları değiştirilemez veya silinemez'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    for table_name in IMMUTABLE_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_append_only
            BEFORE UPDATE OR DELETE OR TRUNCATE ON {table_name}
            FOR EACH STATEMENT
            EXECUTE FUNCTION reject_fulfillment_mutation()
            """
        )


def downgrade() -> None:
    for table_name in reversed(IMMUTABLE_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table_name}_append_only ON {table_name}")
    op.execute("DROP FUNCTION IF EXISTS reject_fulfillment_mutation()")
    for table_name in reversed(IMMUTABLE_TABLES):
        op.drop_table(table_name)
    op.execute("DROP SEQUENCE IF EXISTS production_work_order_seq")
    return_resolution_enum.drop(op.get_bind(), checkfirst=True)
    return_reason_enum.drop(op.get_bind(), checkfirst=True)
