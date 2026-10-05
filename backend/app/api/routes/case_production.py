from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_csrf
from app.api.dependencies.cases import case_access
from app.api.routes.case_errors import raise_case_service_error
from app.db.session import get_db
from app.models import User
from app.schemas.case import CaseResponse
from app.schemas.fulfillment import (
    CaseOperationsResponse,
    ProductionCompleteRequest,
    ProductionStartRequest,
)
from app.services.cases import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
    case_to_response,
    complete_production,
    get_case_operations,
    start_production,
)

router = APIRouter()
CASE_SERVICE_ERRORS = (
    CaseNotFoundError,
    CaseAccessDeniedError,
    CaseConflictError,
    CaseValidationError,
)


@router.get("/{case_id}/operations", response_model=CaseOperationsResponse)
def list_case_operations(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
) -> CaseOperationsResponse:
    try:
        return get_case_operations(db, case_id=case_id, actor=actor)
    except CASE_SERVICE_ERRORS as error:
        raise_case_service_error(error)


@router.post(
    "/{case_id}/production/start",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def start_case_production(
    case_id: UUID,
    payload: ProductionStartRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = start_production(
            db,
            case_id=case_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except CASE_SERVICE_ERRORS as error:
        raise_case_service_error(error)
    return case_to_response(case, actor=actor)


@router.post(
    "/{case_id}/production/complete",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def complete_case_production(
    case_id: UUID,
    payload: ProductionCompleteRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = complete_production(
            db,
            case_id=case_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except CASE_SERVICE_ERRORS as error:
        raise_case_service_error(error)
    return case_to_response(case, actor=actor)
