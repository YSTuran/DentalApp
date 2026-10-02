from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_csrf
from app.api.dependencies.cases import case_access
from app.db.session import get_db
from app.models import CaseStatus, User
from app.schemas.case import (
    CaseCancelRequest,
    CaseClinicOptionResponse,
    CaseCreateOptionsResponse,
    CaseCreateRequest,
    CaseDentistOptionResponse,
    CaseHistoryListResponse,
    CaseListResponse,
    CaseResponse,
    CaseStatusHistoryResponse,
    CaseUpdateRequest,
    ManagerDecisionRequest,
)
from app.services.cases import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
    cancel_case,
    case_to_response,
    create_case,
    get_visible_case,
    list_case_create_options,
    list_case_history,
    list_visible_cases,
    manager_decide_case,
    submit_case,
    update_case,
)

router = APIRouter()

def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="case_not_found")


def _access_denied() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="case_access_denied")


def _raise_service_error(error: Exception) -> None:
    if isinstance(error, CaseNotFoundError):
        raise _not_found() from error
    if isinstance(error, CaseAccessDeniedError):
        raise _access_denied() from error
    if isinstance(error, CaseConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail) from error
    if isinstance(error, CaseValidationError):
        detail: str | dict[str, object] = error.detail
        if error.context:
            detail = {"code": error.detail, **error.context}
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        ) from error
    raise error


@router.get("/create-options", response_model=CaseCreateOptionsResponse)
def get_case_create_options(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
) -> CaseCreateOptionsResponse:
    return CaseCreateOptionsResponse(
        clinics=[
            CaseClinicOptionResponse(
                id=clinic.id,
                code=clinic.code,
                name=clinic.name,
                dentists=[
                    CaseDentistOptionResponse(id=dentist.id, full_name=dentist.full_name)
                    for dentist in dentists
                ],
            )
            for clinic, dentists in list_case_create_options(db, actor=actor)
        ]
    )


@router.get("", response_model=CaseListResponse, response_model_exclude_none=True)
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    case_status: Annotated[CaseStatus | None, Query(alias="status")] = None,
    clinic_id: UUID | None = None,
    responsible_dentist_user_id: UUID | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CaseListResponse:
    try:
        cases, total = list_visible_cases(
            db,
            actor=actor,
            status=case_status,
            clinic_id=clinic_id,
            responsible_dentist_user_id=responsible_dentist_user_id,
            search=search,
            limit=limit,
            offset=offset,
        )
    except (CaseAccessDeniedError, CaseValidationError) as error:
        _raise_service_error(error)

    return CaseListResponse(
        items=[case_to_response(case, actor=actor) for case in cases],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=CaseResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_new_case(
    payload: CaseCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = create_case(db, payload=payload, actor=actor, request=request)
    except (CaseAccessDeniedError, CaseValidationError) as error:
        _raise_service_error(error)
    return case_to_response(case, actor=actor)


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def get_case(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
) -> CaseResponse:
    try:
        case = get_visible_case(db, actor=actor, case_id=case_id)
    except (CaseNotFoundError, CaseAccessDeniedError) as error:
        _raise_service_error(error)
    return case_to_response(case, actor=actor)


@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def update_existing_case(
    case_id: UUID,
    payload: CaseUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = update_case(
            db,
            case_id=case_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except (
        CaseNotFoundError,
        CaseAccessDeniedError,
        CaseConflictError,
        CaseValidationError,
    ) as error:
        _raise_service_error(error)
    return case_to_response(case, actor=actor)


@router.post(
    "/{case_id}/submit",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def submit_existing_case(
    case_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = submit_case(db, case_id=case_id, actor=actor, request=request)
    except (
        CaseNotFoundError,
        CaseAccessDeniedError,
        CaseConflictError,
        CaseValidationError,
    ) as error:
        _raise_service_error(error)
    return case_to_response(case, actor=actor)


@router.post(
    "/{case_id}/manager-decision",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def decide_manager_review(
    case_id: UUID,
    payload: ManagerDecisionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = manager_decide_case(
            db,
            case_id=case_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except (
        CaseNotFoundError,
        CaseAccessDeniedError,
        CaseConflictError,
        CaseValidationError,
    ) as error:
        _raise_service_error(error)
    return case_to_response(case, actor=actor)


@router.post(
    "/{case_id}/cancel",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def cancel_existing_case(
    case_id: UUID,
    payload: CaseCancelRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = cancel_case(
            db,
            case_id=case_id,
            reason=payload.reason,
            actor=actor,
            request=request,
        )
    except (
        CaseNotFoundError,
        CaseAccessDeniedError,
        CaseConflictError,
        CaseValidationError,
    ) as error:
        _raise_service_error(error)
    return case_to_response(case, actor=actor)


@router.get("/{case_id}/history", response_model=CaseHistoryListResponse)
def get_case_history(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
) -> CaseHistoryListResponse:
    try:
        history = list_case_history(db, actor=actor, case_id=case_id)
    except (CaseNotFoundError, CaseAccessDeniedError) as error:
        _raise_service_error(error)
    return CaseHistoryListResponse(
        items=[CaseStatusHistoryResponse.model_validate(item) for item in history]
    )
