from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import ColorPalette, ThemeMode


class UserPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme_mode: ThemeMode = ThemeMode.SYSTEM
    color_palette: ColorPalette = ColorPalette.DEFAULT
    updated_at: datetime | None = None


class UserPreferenceUpdateRequest(BaseModel):
    theme_mode: ThemeMode | None = None
    color_palette: ColorPalette | None = None

    @model_validator(mode="after")
    def require_preference(self) -> "UserPreferenceUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Güncellenecek en az bir görünüm tercihi gönderilmelidir.")
        if "theme_mode" in self.model_fields_set and self.theme_mode is None:
            raise ValueError("Tema modu null olamaz.")
        if "color_palette" in self.model_fields_set and self.color_palette is None:
            raise ValueError("Renk paleti null olamaz.")
        return self
