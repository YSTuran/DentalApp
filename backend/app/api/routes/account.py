from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_csrf
from app.db.session import get_db
from app.models import User
from app.schemas.preference import UserPreferenceResponse, UserPreferenceUpdateRequest
from app.services.preferences import (
    PreferenceValidationError,
    get_user_preferences,
    update_user_preferences,
)

router = APIRouter()


@router.get("/preferences", response_model=UserPreferenceResponse)
def current_preferences(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(get_current_user)],
) -> UserPreferenceResponse:
    return get_user_preferences(db, actor=actor)


@router.patch("/preferences", response_model=UserPreferenceResponse)
def update_current_preferences(
    payload: UserPreferenceUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> UserPreferenceResponse:
    try:
        return update_user_preferences(
            db,
            payload=payload,
            actor=actor,
            request=request,
        )
    except PreferenceValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error.detail,
        ) from error
