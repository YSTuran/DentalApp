from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.encrypted_types import EncryptedText
from app.models.enums import CaseTransferStatus

TRANSFER_STATUS_ENUM = Enum(
    CaseTransferStatus,
    name="case_transfer_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda enum: [item.value for item in enum],
)


class CaseTransfer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_transfers"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    from_dentist_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    to_dentist_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decided_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[CaseTransferStatus] = mapped_column(
        TRANSFER_STATUS_ENUM,
        nullable=False,
        default=CaseTransferStatus.PENDING,
        server_default=CaseTransferStatus.PENDING.value,
    )
    request_reason: Mapped[str] = mapped_column(
        EncryptedText("case_transfers.request_reason"), nullable=False
    )
    decision_reason: Mapped[str | None] = mapped_column(
        EncryptedText("case_transfers.decision_reason"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case = relationship("DentalCase", back_populates="transfers")
    from_dentist = relationship("User", foreign_keys=[from_dentist_user_id])
    to_dentist = relationship("User", foreign_keys=[to_dentist_user_id])
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    decided_by = relationship("User", foreign_keys=[decided_by_user_id])

    __table_args__ = (
        CheckConstraint(
            "from_dentist_user_id <> to_dentist_user_id",
            name="different_dentists",
        ),
        CheckConstraint(
            "(status = 'pending' AND decided_by_user_id IS NULL AND decided_at IS NULL "
            "AND decision_reason IS NULL) OR "
            "(status IN ('accepted', 'rejected') AND decided_by_user_id IS NOT NULL "
            "AND decided_at IS NOT NULL)",
            name="decision_state",
        ),
        Index(
            "uq_case_transfers_pending_case",
            "case_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_case_transfers_target_status", "to_dentist_user_id", "status"),
    )
