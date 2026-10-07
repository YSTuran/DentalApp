from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_csrf
from app.api.dependencies.authorization import require_any_role, require_system_admin
from app.db.session import get_db
from app.models import RoleCode, User
from app.schemas.user_management import (
    ClinicAssignmentCreateRequest,
    ClinicAssignmentResponse,
    ManagedUserListResponse,
    ManagedUserResponse,
    ReasonRequest,
    RoleAssignmentCreateRequest,
    RoleAssignmentResponse,
    RoleAssignmentUpdateRequest,
    UserCreatedResponse,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.services.user_clinics import assign_clinic, change_clinic_assignment_status
from app.services.user_errors import ClinicAssignmentNotFoundError
from app.services.users import (
    FirebaseSyncError,
    RoleAssignmentNotFoundError,
    UserAccessDeniedError,
    UserConflictError,
    UserNotFoundError,
    UserValidationError,
    assign_role,
    change_role_status,
    change_user_status,
    create_user,
    get_visible_user,
    list_visible_clinic_assignments,
    list_visible_role_assignments,
    list_visible_users,
    replace_role_assignment,
    update_user,
)

router = APIRouter()
user_read_access = require_any_role(RoleCode.SYSTEM_ADMIN, RoleCode.CLINIC_MANAGER)


def _user_response(user: User, actor: User) -> ManagedUserResponse:
    return ManagedUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        role_assignments=[
            RoleAssignmentResponse.model_validate(assignment)
            for assignment in list_visible_role_assignments(actor=actor, user=user)
        ],
        clinic_assignments=[
            ClinicAssignmentResponse.model_validate(assignment)
            for assignment in list_visible_clinic_assignments(actor=actor, user=user)
        ],
    )


def _translate_service_error(error: Exception) -> HTTPException:
    if isinstance(error, UserNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    if isinstance(error, RoleAssignmentNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role_assignment_not_found",
        )
    if isinstance(error, ClinicAssignmentNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="clinic_assignment_not_found",
        )
    if isinstance(error, UserAccessDeniedError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_access_denied",
        )
    if isinstance(error, UserConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail)
    if isinstance(error, UserValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error.detail,
        )
    if isinstance(error, FirebaseSyncError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error.detail,
        )
    raise error


@router.get("", response_model=ManagedUserListResponse)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(user_read_access)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_active: bool | None = None,
    role: RoleCode | None = None,
    clinic_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ManagedUserListResponse:
    try:
        users, total = list_visible_users(
            db,
            actor=actor,
            search=search,
            is_active=is_active,
            role=role,
            clinic_id=clinic_id,
            limit=limit,
            offset=offset,
        )
    except (UserAccessDeniedError, UserValidationError) as error:
        raise _translate_service_error(error) from error

    return ManagedUserListResponse(
        items=[_user_response(user, actor) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{user_id}", response_model=ManagedUserResponse)
def get_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(user_read_access)],
) -> ManagedUserResponse:
    try:
        user = get_visible_user(db, actor=actor, user_id=user_id)
    except (UserNotFoundError, UserAccessDeniedError) as error:
        raise _translate_service_error(error) from error
    return _user_response(user, actor)


@router.post("", response_model=UserCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_new_user(
    payload: UserCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> UserCreatedResponse:
    try:
        user, temporary_password = create_user(
            db,
            payload=payload,
            actor=actor,
            request=request,
        )
    except (UserConflictError, UserValidationError, FirebaseSyncError) as error:
        raise _translate_service_error(error) from error
    return UserCreatedResponse(
        user=_user_response(user, actor),
        temporary_password=temporary_password,
    )


@router.patch("/{user_id}", response_model=ManagedUserResponse)
def update_existing_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ManagedUserResponse:
    try:
        user = update_user(
            db,
            user_id=user_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except (UserNotFoundError, UserConflictError, FirebaseSyncError) as error:
        raise _translate_service_error(error) from error
    return _user_response(user, actor)


@router.post("/{user_id}/deactivate", response_model=ManagedUserResponse)
def deactivate_user(
    user_id: UUID,
    payload: ReasonRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ManagedUserResponse:
    return _change_user_status(
        db=db,
        user_id=user_id,
        is_active=False,
        reason=payload.reason,
        actor=actor,
        request=request,
    )


@router.post("/{user_id}/reactivate", response_model=ManagedUserResponse)
def reactivate_user(
    user_id: UUID,
    payload: ReasonRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ManagedUserResponse:
    return _change_user_status(
        db=db,
        user_id=user_id,
        is_active=True,
        reason=payload.reason,
        actor=actor,
        request=request,
    )


def _change_user_status(
    *,
    db: Session,
    user_id: UUID,
    is_active: bool,
    reason: str,
    actor: User,
    request: Request,
) -> ManagedUserResponse:
    try:
        user = change_user_status(
            db,
            user_id=user_id,
            is_active=is_active,
            reason=reason,
            actor=actor,
            request=request,
        )
    except (UserNotFoundError, UserConflictError, FirebaseSyncError) as error:
        raise _translate_service_error(error) from error
    return _user_response(user, actor)


@router.post(
    "/{user_id}/roles",
    response_model=RoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_role(
    user_id: UUID,
    payload: RoleAssignmentCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> RoleAssignmentResponse:
    try:
        assignment = assign_role(
            db,
            user_id=user_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except (UserNotFoundError, UserConflictError, UserValidationError) as error:
        raise _translate_service_error(error) from error
    return RoleAssignmentResponse.model_validate(assignment)


@router.patch(
    "/{user_id}/roles/{assignment_id}",
    response_model=RoleAssignmentResponse,
)
def change_role_assignment(
    user_id: UUID,
    assignment_id: UUID,
    payload: RoleAssignmentUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> RoleAssignmentResponse:
    try:
        assignment = replace_role_assignment(
            db,
            user_id=user_id,
            assignment_id=assignment_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except (
        UserNotFoundError,
        RoleAssignmentNotFoundError,
        UserConflictError,
        UserValidationError,
    ) as error:
        raise _translate_service_error(error) from error
    return RoleAssignmentResponse.model_validate(assignment)


@router.post(
    "/{user_id}/roles/{assignment_id}/deactivate",
    response_model=RoleAssignmentResponse,
)
def deactivate_role(
    user_id: UUID,
    assignment_id: UUID,
    payload: ReasonRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> RoleAssignmentResponse:
    return _change_role_status(
        db=db,
        user_id=user_id,
        assignment_id=assignment_id,
        is_active=False,
        reason=payload.reason,
        actor=actor,
        request=request,
    )


@router.post(
    "/{user_id}/roles/{assignment_id}/reactivate",
    response_model=RoleAssignmentResponse,
)
def reactivate_role(
    user_id: UUID,
    assignment_id: UUID,
    payload: ReasonRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> RoleAssignmentResponse:
    return _change_role_status(
        db=db,
        user_id=user_id,
        assignment_id=assignment_id,
        is_active=True,
        reason=payload.reason,
        actor=actor,
        request=request,
    )


def _change_role_status(
    *,
    db: Session,
    user_id: UUID,
    assignment_id: UUID,
    is_active: bool,
    reason: str,
    actor: User,
    request: Request,
) -> RoleAssignmentResponse:
    try:
        assignment = change_role_status(
            db,
            user_id=user_id,
            assignment_id=assignment_id,
            is_active=is_active,
            reason=reason,
            actor=actor,
            request=request,
        )
    except (
        UserNotFoundError,
        RoleAssignmentNotFoundError,
        UserConflictError,
        UserValidationError,
    ) as error:
        raise _translate_service_error(error) from error
    return RoleAssignmentResponse.model_validate(assignment)


@router.post(
    "/{user_id}/clinics",
    response_model=ClinicAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_clinic_assignment(
    user_id: UUID,
    payload: ClinicAssignmentCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ClinicAssignmentResponse:
    try:
        assignment = assign_clinic(
            db,
            user_id=user_id,
            clinic_id=payload.clinic_id,
            reason=payload.reason,
            actor=actor,
            request=request,
        )
    except (UserNotFoundError, UserConflictError, UserValidationError) as error:
        raise _translate_service_error(error) from error
    return ClinicAssignmentResponse.model_validate(assignment)


@router.post(
    "/{user_id}/clinics/{assignment_id}/deactivate",
    response_model=ClinicAssignmentResponse,
)
def deactivate_clinic_assignment(
    user_id: UUID,
    assignment_id: UUID,
    payload: ReasonRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ClinicAssignmentResponse:
    return _change_clinic_assignment_status(
        db=db,
        user_id=user_id,
        assignment_id=assignment_id,
        is_active=False,
        reason=payload.reason,
        actor=actor,
        request=request,
    )


@router.post(
    "/{user_id}/clinics/{assignment_id}/reactivate",
    response_model=ClinicAssignmentResponse,
)
def reactivate_clinic_assignment(
    user_id: UUID,
    assignment_id: UUID,
    payload: ReasonRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ClinicAssignmentResponse:
    return _change_clinic_assignment_status(
        db=db,
        user_id=user_id,
        assignment_id=assignment_id,
        is_active=True,
        reason=payload.reason,
        actor=actor,
        request=request,
    )


def _change_clinic_assignment_status(
    *,
    db: Session,
    user_id: UUID,
    assignment_id: UUID,
    is_active: bool,
    reason: str,
    actor: User,
    request: Request,
) -> ClinicAssignmentResponse:
    try:
        assignment = change_clinic_assignment_status(
            db,
            user_id=user_id,
            assignment_id=assignment_id,
            is_active=is_active,
            reason=reason,
            actor=actor,
            request=request,
        )
    except (
        UserNotFoundError,
        ClinicAssignmentNotFoundError,
        UserConflictError,
        UserValidationError,
    ) as error:
        raise _translate_service_error(error) from error
    return ClinicAssignmentResponse.model_validate(assignment)
