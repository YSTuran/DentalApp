"""encrypt patient identity fields

Revision ID: e5c7a9d2f4b6
Revises: d4a8f2c6e1b3
Create Date: 2026-10-06 15:30:00
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

from app.core.patient_data import get_patient_data_cipher

revision: str = "e5c7a9d2f4b6"
down_revision: str | Sequence[str] | None = "d4a8f2c6e1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("patient_code_encrypted", sa.LargeBinary(), nullable=True))
    op.add_column("cases", sa.Column("patient_code_lookup", sa.LargeBinary(32), nullable=True))
    op.add_column("cases", sa.Column("patient_name_encrypted", sa.LargeBinary(), nullable=True))

    connection = op.get_bind()
    cipher = get_patient_data_cipher()
    rows = connection.execute(
        sa.text("SELECT id, patient_code, patient_name FROM cases")
    ).mappings()
    for row in rows:
        case_id = UUID(str(row["id"]))
        patient_code = row["patient_code"]
        patient_name = row["patient_name"]
        connection.execute(
            sa.text(
                """
                UPDATE cases
                SET patient_code_encrypted = :patient_code_encrypted,
                    patient_code_lookup = :patient_code_lookup,
                    patient_name_encrypted = :patient_name_encrypted
                WHERE id = :case_id
                """
            ),
            {
                "case_id": case_id,
                "patient_code_encrypted": (
                    cipher.encrypt(patient_code, case_id=case_id, field="patient_code")
                    if patient_code
                    else None
                ),
                "patient_code_lookup": (
                    cipher.lookup_digest(patient_code) if patient_code else None
                ),
                "patient_name_encrypted": (
                    cipher.encrypt(patient_name, case_id=case_id, field="patient_name")
                    if patient_name
                    else None
                ),
            },
        )

    op.create_index("ix_cases_patient_code_lookup", "cases", ["patient_code_lookup"])
    op.drop_column("cases", "patient_name")
    op.drop_column("cases", "patient_code")


def downgrade() -> None:
    op.add_column("cases", sa.Column("patient_code", sa.String(length=100), nullable=True))
    op.add_column("cases", sa.Column("patient_name", sa.String(length=200), nullable=True))

    connection = op.get_bind()
    cipher = get_patient_data_cipher()
    rows = connection.execute(
        sa.text(
            "SELECT id, patient_code_encrypted, patient_name_encrypted FROM cases"
        )
    ).mappings()
    for row in rows:
        case_id = UUID(str(row["id"]))
        patient_code_encrypted = row["patient_code_encrypted"]
        patient_name_encrypted = row["patient_name_encrypted"]
        connection.execute(
            sa.text(
                """
                UPDATE cases
                SET patient_code = :patient_code,
                    patient_name = :patient_name
                WHERE id = :case_id
                """
            ),
            {
                "case_id": case_id,
                "patient_code": (
                    cipher.decrypt(
                        bytes(patient_code_encrypted),
                        case_id=case_id,
                        field="patient_code",
                    )
                    if patient_code_encrypted
                    else None
                ),
                "patient_name": (
                    cipher.decrypt(
                        bytes(patient_name_encrypted),
                        case_id=case_id,
                        field="patient_name",
                    )
                    if patient_name_encrypted
                    else None
                ),
            },
        )

    op.drop_index("ix_cases_patient_code_lookup", table_name="cases")
    op.drop_column("cases", "patient_name_encrypted")
    op.drop_column("cases", "patient_code_lookup")
    op.drop_column("cases", "patient_code_encrypted")
