from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ColorPalette, ThemeMode

if TYPE_CHECKING:
    from app.models.clinic import Clinic
    from app.models.user import User


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    theme_mode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ThemeMode.LIGHT.value,
        server_default=ThemeMode.LIGHT.value,
    )
    color_palette: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ColorPalette.DEFAULT.value,
        server_default=ColorPalette.DEFAULT.value,
    )
    active_clinic_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("clinics.id", ondelete="RESTRICT"),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="preference")
    active_clinic: Mapped["Clinic | None"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "theme_mode IN ('light', 'dark', 'system')",
            name="theme_mode",
        ),
        CheckConstraint(
            "color_palette IN ("
            "'default', 'ocean', 'violet', 'arctic', 'sage', 'graphite', "
            "'amber', 'burgundy', 'coral', 'sepia', 'high_contrast'"
            ")",
            name="color_palette",
        ),
    )
