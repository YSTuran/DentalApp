from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EmailOutbox(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "email_outbox"

    notification_id: Mapped[UUID] = mapped_column(
        ForeignKey("notifications.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    recipient_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'retry', 'sent', 'failed')",
            name="status_valid",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        CheckConstraint("length(btrim(recipient_email)) > 0", name="recipient_required"),
        Index("ix_email_outbox_dispatch", "status", "next_attempt_at"),
    )
