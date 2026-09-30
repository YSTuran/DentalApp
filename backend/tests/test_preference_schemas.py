import pytest
from pydantic import ValidationError

from app.models import ColorPalette, ThemeMode
from app.schemas.preference import UserPreferenceResponse, UserPreferenceUpdateRequest


def test_default_preferences_follow_system_theme() -> None:
    preferences = UserPreferenceResponse()

    assert preferences.theme_mode == ThemeMode.SYSTEM
    assert preferences.color_palette == ColorPalette.DEFAULT


def test_preference_update_requires_at_least_one_valid_value() -> None:
    with pytest.raises(ValidationError):
        UserPreferenceUpdateRequest()

    with pytest.raises(ValidationError):
        UserPreferenceUpdateRequest(theme_mode="unknown")


def test_preference_update_accepts_mode_and_palette() -> None:
    payload = UserPreferenceUpdateRequest(theme_mode="dark", color_palette="ocean")

    assert payload.theme_mode == ThemeMode.DARK
    assert payload.color_palette == ColorPalette.OCEAN


@pytest.mark.parametrize("palette", list(ColorPalette))
def test_preference_update_accepts_every_color_palette(palette: ColorPalette) -> None:
    payload = UserPreferenceUpdateRequest(color_palette=palette.value)

    assert payload.color_palette == palette
