from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_csrf
from app.api.dependencies.authorization import (
    require_any_role,
    require_clinic_roles,
    require_system_admin,
)
from app.db.session import get_db
from app.models import RoleCode, User
from app.schemas.clinic import (
    ClinicCreateRequest,
    ClinicListResponse,
    ClinicResponse,
    ClinicStatusChangeRequest,
    ClinicUpdateRequest,
)
from app.services.clinics import (
    ClinicAccessDeniedError,
    ClinicCodeConflictError,
    ClinicNoChangesError,
    ClinicNotFoundError,
    ClinicStateConflictError,
    change_clinic_status,
    create_clinic,
    get_visible_clinic,
    list_visible_clinics,
    update_clinic,
)

router = APIRouter()

clinic_list_access = require_any_role(RoleCode.SYSTEM_ADMIN, RoleCode.CLINIC_MANAGER)
clinic_detail_access = require_clinic_roles(
    RoleCode.CLINIC_MANAGER,
    allow_system_admin=True,
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="clinic_not_found")


def _access_denied() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="clinic_access_denied",
    )


@router.get("", response_model=ClinicListResponse)
def list_clinics(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(clinic_list_access)],
    is_active: bool | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ClinicListResponse:
    try:
        clinics, total = list_visible_clinics(
            db,
            actor=actor,
            is_active=is_active,
            search=search,
            limit=limit,
            offset=offset,
        )
    except ClinicAccessDeniedError as error:
        raise _access_denied() from error

    return ClinicListResponse(items=clinics, total=total, limit=limit, offset=offset)


@router.get("/{clinic_id}", response_model=ClinicResponse)
def get_clinic(
    clinic_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(clinic_detail_access)],
) -> ClinicResponse:
    try:
        return ClinicResponse.model_validate(
            get_visible_clinic(db, actor=actor, clinic_id=clinic_id)
        )
    except ClinicNotFoundError as error:
        raise _not_found() from error
    except ClinicAccessDeniedError as error:
        raise _access_denied() from error


@router.post("", response_model=ClinicResponse, status_code=status.HTTP_201_CREATED)
def create_new_clinic(
    payload: ClinicCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ClinicResponse:
    try:
        clinic = create_clinic(db, payload=payload, actor=actor, request=request)
    except ClinicCodeConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="clinic_code_exists",
        ) from error
    except ClinicAccessDeniedError as error:
        raise _access_denied() from error
    return ClinicResponse.model_validate(clinic)


@router.patch("/{clinic_id}", response_model=ClinicResponse)
def update_existing_clinic(
    clinic_id: UUID,
    payload: ClinicUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ClinicResponse:
    try:
        clinic = update_clinic(
            db,
            clinic_id=clinic_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except ClinicNotFoundError as error:
        raise _not_found() from error
    except ClinicCodeConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="clinic_code_exists",
        ) from error
    except ClinicNoChangesError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="clinic_no_changes",
        ) from error
    except ClinicAccessDeniedError as error:
        raise _access_denied() from error
    return ClinicResponse.model_validate(clinic)


@router.post("/{clinic_id}/deactivate", response_model=ClinicResponse)
def deactivate_clinic(
    clinic_id: UUID,
    payload: ClinicStatusChangeRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ClinicResponse:
    return _change_status(
        db=db,
        clinic_id=clinic_id,
        is_active=False,
        reason=payload.reason,
        actor=actor,
        request=request,
    )


@router.post("/{clinic_id}/reactivate", response_model=ClinicResponse)
def reactivate_clinic(
    clinic_id: UUID,
    payload: ClinicStatusChangeRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_system_admin)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> ClinicResponse:
    return _change_status(
        db=db,
        clinic_id=clinic_id,
        is_active=True,
        reason=payload.reason,
        actor=actor,
        request=request,
    )


def _change_status(
    *,
    db: Session,
    clinic_id: UUID,
    is_active: bool,
    reason: str,
    actor: User,
    request: Request,
) -> ClinicResponse:
    try:
        clinic = change_clinic_status(
            db,
            clinic_id=clinic_id,
            is_active=is_active,
            reason=reason,
            actor=actor,
            request=request,
        )
    except ClinicNotFoundError as error:
        raise _not_found() from error
    except ClinicStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.detail,
        ) from error
    except ClinicAccessDeniedError as error:
        raise _access_denied() from error
    return ClinicResponse.model_validate(clinic)
