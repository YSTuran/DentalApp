from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.case import CASE_STATUS_ENUM
from app.models.enums import CaseStatus


class CaseWaitAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_wait_alerts"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    case_status: Mapped[CaseStatus] = mapped_column(CASE_STATUS_ENUM, nullable=False)
    recipient_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notification_id: Mapped[UUID] = mapped_column(
        ForeignKey("notifications.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    stage_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    threshold_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint("threshold_hours > 0", name="threshold_hours_positive"),
        UniqueConstraint(
            "case_id",
            "case_status",
            "recipient_user_id",
            "stage_started_at",
            name="uq_case_wait_alert_stage_recipient",
        ),
        Index("ix_case_wait_alerts_case_status", "case_id", "case_status"),
    )
