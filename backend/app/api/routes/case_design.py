from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_csrf
from app.api.dependencies.cases import case_access
from app.api.routes.case_errors import raise_case_service_error
from app.db.session import get_db
from app.models import User
from app.schemas.case import CaseResponse, DentistDecisionRequest, DesignSubmitRequest
from app.services.cases import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
    case_to_response,
    dentist_decide_design,
    submit_design,
)

router = APIRouter()
CASE_SERVICE_ERRORS = (
    CaseNotFoundError,
    CaseAccessDeniedError,
    CaseConflictError,
    CaseValidationError,
)


@router.post(
    "/{case_id}/design-submit",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def submit_case_design(
    case_id: UUID,
    payload: DesignSubmitRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = submit_design(
            db,
            case_id=case_id,
            file_version_id=payload.file_version_id,
            actor=actor,
            request=request,
        )
    except CASE_SERVICE_ERRORS as error:
        raise_case_service_error(error)
    return case_to_response(case, actor=actor)


@router.post(
    "/{case_id}/dentist-decision",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def decide_case_design(
    case_id: UUID,
    payload: DentistDecisionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = dentist_decide_design(
            db,
            case_id=case_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except CASE_SERVICE_ERRORS as error:
        raise_case_service_error(error)
    return case_to_response(case, actor=actor)
