"""encrypt sensitive case fields and free-text reasons

Revision ID: e2a7c5d9f1b4
Revises: d1f6b8c3a9e2
Create Date: 2026-10-07 20:00:00
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.sensitive_data import get_sensitive_data_cipher

revision: str = "e2a7c5d9f1b4"
down_revision: str | Sequence[str] | None = "d1f6b8c3a9e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


@dataclass(frozen=True)
class ProtectedColumn:
    table: str
    key: str
    column: str
    purpose: str
    kind: str = "text"
    nullable: bool = True


COLUMNS = (
    ProtectedColumn(
        "case_details",
        "case_id",
        "tooth_numbers",
        "case_details.tooth_numbers",
        "json",
        False,
    ),
    ProtectedColumn("case_details", "case_id", "special_notes", "case_details.special_notes"),
    ProtectedColumn(
        "case_details",
        "case_id",
        "extra_fields",
        "case_details.extra_fields",
        "json",
        False,
    ),
    ProtectedColumn(
        "case_file_versions",
        "id",
        "original_filename",
        "case_file_versions.original_filename",
        nullable=False,
    ),
    ProtectedColumn(
        "case_upload_sessions",
        "id",
        "original_filename",
        "case_upload_sessions.original_filename",
        nullable=False,
    ),
    ProtectedColumn("case_approvals", "id", "reason", "case_approvals.reason"),
    ProtectedColumn("case_status_history", "id", "reason", "case_status_history.reason"),
    ProtectedColumn(
        "case_transfers",
        "id",
        "request_reason",
        "case_transfers.request_reason",
        nullable=False,
    ),
    ProtectedColumn("case_transfers", "id", "decision_reason", "case_transfers.decision_reason"),
    ProtectedColumn("audit_events", "id", "reason", "audit_events.reason"),
    ProtectedColumn("production_runs", "id", "notes", "production_runs.notes"),
    ProtectedColumn(
        "production_completions",
        "id",
        "notes",
        "production_completions.notes",
    ),
    ProtectedColumn("shipments", "id", "notes", "shipments.notes"),
    ProtectedColumn("delivery_confirmations", "id", "notes", "delivery_confirmations.notes"),
    ProtectedColumn("return_receipts", "id", "reason", "return_receipts.reason", nullable=False),
    ProtectedColumn(
        "return_receipts",
        "id",
        "inspection_notes",
        "return_receipts.inspection_notes",
    ),
    ProtectedColumn("return_decisions", "id", "reason", "return_decisions.reason", nullable=False),
)

TABLES = tuple(dict.fromkeys(item.table for item in COLUMNS))


def _set_triggers(enabled: bool) -> None:
    action = "ENABLE" if enabled else "DISABLE"
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" {action} TRIGGER USER')


def _drop_plaintext_constraints() -> None:
    constraints = (
        ("case_details", "ck_case_details_tooth_numbers_array"),
        ("case_details", "ck_case_details_extra_fields_object"),
        (
            "case_approvals",
            "ck_case_approvals_ck_case_approvals_decision_reason_required",
        ),
        ("case_transfers", "ck_case_transfers_request_reason_required"),
        ("case_transfers", "ck_case_transfers_rejection_reason_required"),
        ("return_receipts", "ck_return_receipts_return_reason_required"),
        ("return_decisions", "ck_return_decisions_return_decision_reason_required"),
    )
    for table, name in constraints:
        op.drop_constraint(op.f(name), table, type_="check")


def _encrypt_column(item: ProtectedColumn) -> None:
    bind = op.get_bind()
    temporary = f"{item.column}_encrypted"
    op.add_column(item.table, sa.Column(temporary, sa.LargeBinary(), nullable=True))
    rows = (
        bind.execute(
            sa.text(f'SELECT "{item.key}" AS row_key, "{item.column}" AS value FROM "{item.table}"')
        )
        .mappings()
        .all()
    )
    cipher = get_sensitive_data_cipher()
    for row in rows:
        value = row["value"]
        if value is None:
            continue
        encrypted = (
            cipher.encrypt_json(value, purpose=item.purpose)
            if item.kind == "json"
            else cipher.encrypt_text(value, purpose=item.purpose)
        )
        bind.execute(
            sa.text(
                f'UPDATE "{item.table}" SET "{temporary}" = :value WHERE "{item.key}" = :row_key'
            ),
            {"value": encrypted, "row_key": row["row_key"]},
        )
    if not item.nullable:
        op.alter_column(item.table, temporary, nullable=False)
    op.drop_column(item.table, item.column)
    op.alter_column(item.table, temporary, new_column_name=item.column)


def _decrypt_column(item: ProtectedColumn) -> None:
    bind = op.get_bind()
    temporary = f"{item.column}_plaintext"
    target_type: sa.types.TypeEngine = (
        postgresql.JSONB(astext_type=sa.Text()) if item.kind == "json" else sa.Text()
    )
    op.add_column(item.table, sa.Column(temporary, target_type, nullable=True))
    rows = (
        bind.execute(
            sa.text(f'SELECT "{item.key}" AS row_key, "{item.column}" AS value FROM "{item.table}"')
        )
        .mappings()
        .all()
    )
    cipher = get_sensitive_data_cipher()
    for row in rows:
        value = row["value"]
        if value is None:
            continue
        decrypted = (
            cipher.decrypt_json(bytes(value), purpose=item.purpose)
            if item.kind == "json"
            else cipher.decrypt_text(bytes(value), purpose=item.purpose)
        )
        assignment = "CAST(:value AS jsonb)" if item.kind == "json" else ":value"
        bind.execute(
            sa.text(
                f'UPDATE "{item.table}" SET "{temporary}" = {assignment} '
                f'WHERE "{item.key}" = :row_key'
            ),
            {
                "value": json.dumps(decrypted, ensure_ascii=False)
                if item.kind == "json"
                else decrypted,
                "row_key": row["row_key"],
            },
        )
    if not item.nullable:
        op.alter_column(item.table, temporary, nullable=False)
    op.drop_column(item.table, item.column)
    op.alter_column(item.table, temporary, new_column_name=item.column)


def upgrade() -> None:
    _set_triggers(False)
    _drop_plaintext_constraints()
    for item in COLUMNS:
        _encrypt_column(item)
    op.create_check_constraint(
        op.f("ck_case_approvals_decision_reason_required"),
        "case_approvals",
        "decision = 'approved' OR reason IS NOT NULL",
    )
    _set_triggers(True)


def downgrade() -> None:
    _set_triggers(False)
    op.drop_constraint(
        op.f("ck_case_approvals_decision_reason_required"),
        "case_approvals",
        type_="check",
    )
    for item in COLUMNS:
        _decrypt_column(item)
    op.alter_column("case_details", "tooth_numbers", server_default=sa.text("'[]'::jsonb"))
    op.alter_column("case_details", "extra_fields", server_default=sa.text("'{}'::jsonb"))
    op.create_check_constraint(
        op.f("ck_case_details_tooth_numbers_array"),
        "case_details",
        "jsonb_typeof(tooth_numbers) = 'array'",
    )
    op.create_check_constraint(
        op.f("ck_case_details_extra_fields_object"),
        "case_details",
        "jsonb_typeof(extra_fields) = 'object'",
    )
    op.create_check_constraint(
        op.f("ck_case_approvals_decision_reason_required"),
        "case_approvals",
        "decision = 'approved' OR (reason IS NOT NULL AND length(btrim(reason)) >= 3)",
    )
    op.create_check_constraint(
        op.f("ck_case_transfers_request_reason_required"),
        "case_transfers",
        "length(btrim(request_reason)) >= 3",
    )
    op.create_check_constraint(
        op.f("ck_case_transfers_rejection_reason_required"),
        "case_transfers",
        "status <> 'rejected' OR length(btrim(decision_reason)) >= 3",
    )
    op.create_check_constraint(
        op.f("ck_return_receipts_return_reason_required"),
        "return_receipts",
        "length(btrim(reason)) >= 3",
    )
    op.create_check_constraint(
        op.f("ck_return_decisions_return_decision_reason_required"),
        "return_decisions",
        "length(btrim(reason)) >= 3",
    )
    _set_triggers(True)
