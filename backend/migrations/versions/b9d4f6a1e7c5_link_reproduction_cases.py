"""create linked cases for reproduction decisions

Revision ID: b9d4f6a1e7c5
Revises: a8c3e5f0d6b4
Create Date: 2026-10-07 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9d4f6a1e7c5"
down_revision: str | Sequence[str] | None = "a8c3e5f0d6b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    legacy_reproduction = connection.scalar(
        sa.text(
            "SELECT id FROM return_decisions "
            "WHERE resolution::text = 'reproduction' LIMIT 1"
        )
    )
    if legacy_reproduction is not None:
        raise RuntimeError(
            "Yeni vaka bağlantısı olmayan eski yeniden üretim kararı önce taşınmalıdır: "
            f"{legacy_reproduction}"
        )

    op.add_column(
        "cases",
        sa.Column("reproduction_source_case_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_cases_reproduction_source_case_id_cases",
        "cases",
        "cases",
        ["reproduction_source_case_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_cases_reproduction_source_case_id",
        "cases",
        ["reproduction_source_case_id"],
    )

    op.add_column(
        "return_decisions",
        sa.Column("reproduction_case_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_return_decisions_reproduction_case_id_cases",
        "return_decisions",
        "cases",
        ["reproduction_case_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_return_decisions_reproduction_case_id",
        "return_decisions",
        ["reproduction_case_id"],
    )
    op.create_check_constraint(
        "return_decision_reproduction_case",
        "return_decisions",
        "(resolution = 'reproduction' AND reproduction_case_id IS NOT NULL) OR "
        "(resolution = 'rescan' AND reproduction_case_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_return_decisions_return_decision_reproduction_case",
        "return_decisions",
        type_="check",
    )
    op.drop_constraint(
        "uq_return_decisions_reproduction_case_id",
        "return_decisions",
        type_="unique",
    )
    op.drop_constraint(
        "fk_return_decisions_reproduction_case_id_cases",
        "return_decisions",
        type_="foreignkey",
    )
    op.drop_column("return_decisions", "reproduction_case_id")
    op.drop_constraint(
        "uq_cases_reproduction_source_case_id",
        "cases",
        type_="unique",
    )
    op.drop_constraint(
        "fk_cases_reproduction_source_case_id_cases",
        "cases",
        type_="foreignkey",
    )
    op.drop_column("cases", "reproduction_source_case_id")
