from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    case_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("length(btrim(title)) > 0", name="title_required"),
        CheckConstraint("length(btrim(message)) > 0", name="message_required"),
        CheckConstraint(
            "target_path IS NULL OR "
            "(left(target_path, 1) = '/' AND left(target_path, 2) <> '//')",
            name="target_path_internal",
        ),
        Index(
            "ix_notifications_recipient_active_created",
            "recipient_user_id",
            "dismissed_at",
            "created_at",
        ),
        Index("ix_notifications_case_id", "case_id"),
    )
