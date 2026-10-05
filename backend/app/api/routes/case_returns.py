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
from app.schemas.fulfillment import ReturnDecisionRequest, ReturnReceiptCreateRequest
from app.services.cases import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
    case_to_response,
    decide_return,
    register_return_receipt,
)

router = APIRouter()
CASE_SERVICE_ERRORS = (
    CaseNotFoundError,
    CaseAccessDeniedError,
    CaseConflictError,
    CaseValidationError,
)


@router.post(
    "/{case_id}/returns",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def register_case_return(
    case_id: UUID,
    payload: ReturnReceiptCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = register_return_receipt(
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
    "/{case_id}/return-decision",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def decide_case_return(
    case_id: UUID,
    payload: ReturnDecisionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = decide_return(
            db,
            case_id=case_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except CASE_SERVICE_ERRORS as error:
        raise_case_service_error(error)
    return case_to_response(case, actor=actor)
