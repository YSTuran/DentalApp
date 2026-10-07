from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.clinic import Clinic
    from app.models.user import User


class UserClinicAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_clinic_assignments"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "clinic_id",
            name="uq_user_clinic_assignments_user_clinic",
        ),
        Index("ix_user_clinic_assignments_clinic_active", "clinic_id", "is_active"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    user: Mapped["User"] = relationship(back_populates="clinic_assignments")
    clinic: Mapped["Clinic"] = relationship(back_populates="user_assignments")
