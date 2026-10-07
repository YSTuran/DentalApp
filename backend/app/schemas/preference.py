from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import ColorPalette, ThemeMode


class UserPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme_mode: ThemeMode = ThemeMode.LIGHT
    color_palette: ColorPalette = ColorPalette.DEFAULT
    active_clinic_id: UUID | None = None
    updated_at: datetime | None = None


class UserPreferenceUpdateRequest(BaseModel):
    theme_mode: ThemeMode | None = None
    color_palette: ColorPalette | None = None
    active_clinic_id: UUID | None = None

    @model_validator(mode="after")
    def require_preference(self) -> "UserPreferenceUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Güncellenecek en az bir tercih gönderilmelidir.")
        if "theme_mode" in self.model_fields_set and self.theme_mode is None:
            raise ValueError("Tema modu null olamaz.")
        if "color_palette" in self.model_fields_set and self.color_palette is None:
            raise ValueError("Renk paleti null olamaz.")
        return self
