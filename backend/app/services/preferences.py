from fastapi import Request
from sqlalchemy.orm import Session

from app.models import ColorPalette, ThemeMode, User, UserPreference
from app.schemas.preference import UserPreferenceResponse, UserPreferenceUpdateRequest
from app.services.audit import record_audit_event


def serialize_preferences(preference: UserPreference | None) -> UserPreferenceResponse:
    if preference is None:
        return UserPreferenceResponse()
    return UserPreferenceResponse.model_validate(preference)


def get_user_preferences(db: Session, *, actor: User) -> UserPreferenceResponse:
    return serialize_preferences(db.get(UserPreference, actor.id))


def update_user_preferences(
    db: Session,
    *,
    payload: UserPreferenceUpdateRequest,
    actor: User,
    request: Request,
) -> UserPreferenceResponse:
    preference = db.get(UserPreference, actor.id)
    if preference is None:
        preference = UserPreference(
            user_id=actor.id,
            theme_mode=ThemeMode.SYSTEM.value,
            color_palette=ColorPalette.DEFAULT.value,
        )

    before = {
        "theme_mode": preference.theme_mode,
        "color_palette": preference.color_palette,
    }
    if "theme_mode" in payload.model_fields_set:
        preference.theme_mode = payload.theme_mode.value
    if "color_palette" in payload.model_fields_set:
        preference.color_palette = payload.color_palette.value
    after = {
        "theme_mode": preference.theme_mode,
        "color_palette": preference.color_palette,
    }

    if before == after:
        return serialize_preferences(preference)

    try:
        db.add(preference)
        db.flush()
        record_audit_event(
            db,
            action="user.preferences.updated",
            entity_type="user_preference",
            entity_id=actor.id,
            actor=actor,
            before=before,
            after=after,
            context={"source": "self_service"},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(preference)
    return serialize_preferences(preference)
