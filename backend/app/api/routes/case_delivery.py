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
from app.schemas.fulfillment import DeliveryConfirmRequest, ShipmentCreateRequest
from app.services.cases import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
    case_to_response,
    confirm_delivery,
    create_shipment,
)

router = APIRouter()
CASE_SERVICE_ERRORS = (
    CaseNotFoundError,
    CaseAccessDeniedError,
    CaseConflictError,
    CaseValidationError,
)


@router.post(
    "/{case_id}/shipments",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def create_case_shipment(
    case_id: UUID,
    payload: ShipmentCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = create_shipment(
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
    "/{case_id}/delivery-confirmation",
    response_model=CaseResponse,
    response_model_exclude_none=True,
)
def confirm_case_delivery(
    case_id: UUID,
    payload: DeliveryConfirmRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseResponse:
    try:
        case = confirm_delivery(
            db,
            case_id=case_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except CASE_SERVICE_ERRORS as error:
        raise_case_service_error(error)
    return case_to_response(case, actor=actor)
