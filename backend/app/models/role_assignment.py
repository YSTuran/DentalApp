from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Index, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RoleCode

if TYPE_CHECKING:
    from app.models.clinic import Clinic
    from app.models.user import User

ROLE_ENUM = Enum(
    RoleCode,
    name="role_code",
    values_callable=lambda enum: [item.value for item in enum],
)


class UserRoleAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_role_assignments"
    __table_args__ = (
        CheckConstraint(
            "(role IN ('system_admin', 'technician') AND clinic_id IS NULL) OR "
            "(role IN ('clinic_manager', 'managing_dentist', 'dentist', 'clinic_staff') "
            "AND clinic_id IS NOT NULL)",
            name="role_scope",
        ),
        Index(
            "uq_user_role_assignment_global",
            "user_id",
            "role",
            unique=True,
            postgresql_where=text("clinic_id IS NULL"),
        ),
        Index(
            "uq_user_role_assignment_clinic",
            "user_id",
            "role",
            "clinic_id",
            unique=True,
            postgresql_where=text("clinic_id IS NOT NULL"),
        ),
        Index("ix_user_role_assignments_clinic_role", "clinic_id", "role"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role: Mapped[RoleCode] = mapped_column(ROLE_ENUM, nullable=False)
    clinic_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("clinics.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    user: Mapped["User"] = relationship(back_populates="role_assignments")
    clinic: Mapped["Clinic | None"] = relationship(back_populates="role_assignments")
