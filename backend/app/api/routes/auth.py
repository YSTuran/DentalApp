from datetime import timedelta
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import (
    get_current_user,
    get_optional_current_user,
    load_active_user_by_firebase_uid,
    require_csrf,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    ClinicRoleResponse,
    CsrfResponse,
    CurrentUserResponse,
    LogoutResponse,
    SessionRequest,
)
from app.services.audit import record_audit_event
from app.services.firebase_auth import (
    FirebaseAuthenticationError,
    FirebaseServiceError,
    RecentSignInRequiredError,
    create_session_cookie,
)

router = APIRouter()


def serialize_user(user: User) -> CurrentUserResponse:
    active_assignments = [
        assignment for assignment in user.role_assignments if assignment.is_active
    ]
    global_roles = [
        assignment.role for assignment in active_assignments if assignment.clinic_id is None
    ]
    clinic_roles = [
        ClinicRoleResponse(clinic_id=assignment.clinic_id, role=assignment.role)
        for assignment in active_assignments
        if assignment.clinic_id is not None
    ]

    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        global_roles=global_roles,
        clinic_roles=clinic_roles,
    )


@router.get("/csrf", response_model=CsrfResponse)
def issue_csrf_token(response: Response) -> CsrfResponse:
    settings = get_settings()
    csrf_token = token_urlsafe(32)
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return CsrfResponse(csrf_token=csrf_token)


@router.post("/session", response_model=CurrentUserResponse)
def create_session(
    payload: SessionRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUserResponse:
    require_csrf(request)

    try:
        session_cookie, claims = create_session_cookie(payload.id_token)
    except RecentSignInRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="recent_sign_in_required",
        ) from exc
    except FirebaseAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_firebase_token",
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
            detail="invalid_firebase_token",
        )

    user = load_active_user_by_firebase_uid(db, firebase_uid)
    settings = get_settings()
    max_age = int(timedelta(days=settings.firebase_session_days).total_seconds())
    record_audit_event(
        db,
        action="auth.session_created",
        entity_type="user",
        entity_id=user.id,
        actor=user,
        after={"status": "authenticated"},
        context={"provider": "firebase"},
        request=request,
    )
    db.commit()
    response.set_cookie(
        key=settings.firebase_session_cookie_name,
        value=session_cookie,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return serialize_user(user)


@router.get("/me", response_model=CurrentUserResponse)
def current_user(
    user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    return serialize_user(user)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_optional_current_user)],
) -> LogoutResponse:
    require_csrf(request)
    settings = get_settings()
    if user is not None:
        record_audit_event(
            db,
            action="auth.session_ended",
            entity_type="user",
            entity_id=user.id,
            actor=user,
            before={"status": "authenticated"},
            after={"status": "signed_out"},
            context={"provider": "firebase"},
            request=request,
        )
        db.commit()
    response.delete_cookie(
        key=settings.firebase_session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return LogoutResponse()
