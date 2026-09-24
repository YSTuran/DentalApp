from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.services.firebase_auth import (
    FirebaseAuthenticationError,
    FirebaseServiceError,
    verify_session_cookie,
)


def require_csrf(request: Request) -> None:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("X-CSRF-Token")

    if not cookie_token or not header_token or not compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="csrf_validation_failed",
        )


def load_active_user_by_firebase_uid(db: Session, firebase_uid: str) -> User:
    user = db.scalar(
        select(User)
        .options(selectinload(User.role_assignments))
        .where(User.firebase_uid == firebase_uid)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_not_provisioned",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_inactive",
        )

    return user


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    settings = get_settings()
    session_cookie = request.cookies.get(settings.firebase_session_cookie_name)

    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        )

    try:
        claims = verify_session_cookie(session_cookie)
    except FirebaseAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_session",
        ) from exc
    except FirebaseServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication_service_unavailable",
        ) from exc

    firebase_uid = claims.get("uid") or claims.get("sub")
    if not isinstance(firebase_uid, str) or not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_session",
        )

    return load_active_user_by_firebase_uid(db, firebase_uid)


def get_optional_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None
