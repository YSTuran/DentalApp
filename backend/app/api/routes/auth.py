import re
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
from app.models import RoleCode, User
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
from app.services.preferences import serialize_preferences

router = APIRouter()
CSRF_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


def serialize_user(user: User) -> CurrentUserResponse:
    active_roles = [
        assignment for assignment in user.role_assignments if assignment.is_active
    ]
    active_clinics = [
        assignment for assignment in user.clinic_assignments if assignment.is_active
    ]
    global_roles = [
        assignment.role
        for assignment in active_roles
        if assignment.role in {RoleCode.SYSTEM_ADMIN, RoleCode.TECHNICIAN}
    ]
    clinic_roles = [
        ClinicRoleResponse(
            clinic_id=clinic_assignment.clinic_id,
            clinic_name=(
                clinic_assignment.__dict__["clinic"].name
                if clinic_assignment.__dict__.get("clinic") is not None
                else "Klinik"
            ),
            role=role_assignment.role,
        )
        for role_assignment in active_roles
        if role_assignment.role not in {RoleCode.SYSTEM_ADMIN, RoleCode.TECHNICIAN}
        for clinic_assignment in active_clinics
    ]

    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        global_roles=global_roles,
        clinic_roles=clinic_roles,
        preferences=serialize_preferences(user.preference),
    )


def establish_session(payload: SessionRequest, db: Session) -> tuple[str, User]:
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

    return session_cookie, load_active_user_by_firebase_uid(db, firebase_uid)


def set_session_cookie(
    response: Response,
    session_cookie: str,
    *,
    remember_me: bool,
) -> None:
    settings = get_settings()
    max_age = (
        int(timedelta(days=settings.firebase_session_days).total_seconds()) if remember_me else None
    )
    response.set_cookie(
        key=settings.firebase_session_cookie_name,
        value=session_cookie,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/csrf", response_model=CsrfResponse)
def issue_csrf_token(request: Request, response: Response) -> CsrfResponse:
    settings = get_settings()
    current_token = request.cookies.get(settings.csrf_cookie_name)
    csrf_token = (
        current_token
        if current_token is not None and CSRF_TOKEN_PATTERN.fullmatch(current_token)
        else token_urlsafe(32)
    )
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
    session_cookie, user = establish_session(payload, db)
    record_audit_event(
        db,
        action="auth.session_created",
        entity_type="user",
        entity_id=user.id,
        actor=user,
        after={"status": "authenticated"},
        context={"provider": "firebase", "remember_me": payload.remember_me},
        request=request,
    )
    db.commit()
    set_session_cookie(response, session_cookie, remember_me=payload.remember_me)
    return serialize_user(user)


@router.post("/password-changed", response_model=CurrentUserResponse)
def password_changed(
    payload: SessionRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUserResponse:
    require_csrf(request)
    session_cookie, user = establish_session(payload, db)
    record_audit_event(
        db,
        action="account.password_changed",
        entity_type="user",
        entity_id=user.id,
        actor=user,
        context={
            "provider": "firebase",
            "source": "self_service",
            "session_refreshed": True,
            "remember_me": payload.remember_me,
        },
        request=request,
    )
    db.commit()
    set_session_cookie(response, session_cookie, remember_me=payload.remember_me)
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
