from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.clinic_assignment import UserClinicAssignment
    from app.models.role_assignment import UserRoleAssignment
    from app.models.user_preference import UserPreference


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    firebase_uid: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="user",
    )
    clinic_assignments: Mapped[list["UserClinicAssignment"]] = relationship(
        back_populates="user",
    )
    preference: Mapped["UserPreference | None"] = relationship(
        back_populates="user",
        uselist=False,
    )

    __table_args__ = (
        Index("uq_users_email_lower", func.lower(email), unique=True),
        Index("uq_users_firebase_uid", firebase_uid, unique=True),
    )
