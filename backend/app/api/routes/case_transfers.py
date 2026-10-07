from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_csrf
from app.api.dependencies.cases import case_access
from app.api.routes.case_errors import raise_case_service_error
from app.db.session import get_db
from app.models import User
from app.schemas.case_transfer import (
    CaseTransferCreateRequest,
    CaseTransferDecisionRequest,
    CaseTransferListResponse,
    CaseTransferOptionResponse,
    CaseTransferOptionsResponse,
    CaseTransferResponse,
)
from app.services.case_management.transfers import (
    decide_case_transfer,
    list_case_transfers,
    list_transfer_options,
    request_case_transfer,
)
from app.services.cases import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
)

router = APIRouter()


@router.get("/{case_id}/transfer-options", response_model=CaseTransferOptionsResponse)
def get_transfer_options(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
) -> CaseTransferOptionsResponse:
    try:
        users = list_transfer_options(db, actor=actor, case_id=case_id)
    except (CaseNotFoundError, CaseAccessDeniedError) as error:
        raise_case_service_error(error)
    return CaseTransferOptionsResponse(
        items=[CaseTransferOptionResponse(id=user.id, full_name=user.full_name) for user in users]
    )


@router.get("/{case_id}/transfers", response_model=CaseTransferListResponse)
def get_case_transfers(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
) -> CaseTransferListResponse:
    try:
        items = list_case_transfers(db, actor=actor, case_id=case_id)
    except (CaseNotFoundError, CaseAccessDeniedError) as error:
        raise_case_service_error(error)
    return CaseTransferListResponse(items=items)


@router.post(
    "/{case_id}/transfers",
    response_model=CaseTransferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case_transfer(
    case_id: UUID,
    payload: CaseTransferCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseTransferResponse:
    try:
        return request_case_transfer(
            db,
            case_id=case_id,
            to_dentist_user_id=payload.to_dentist_user_id,
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
        raise_case_service_error(error)


@router.post(
    "/{case_id}/transfers/{transfer_id}/decision",
    response_model=CaseTransferResponse,
)
def decide_transfer(
    case_id: UUID,
    transfer_id: UUID,
    payload: CaseTransferDecisionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> CaseTransferResponse:
    try:
        return decide_case_transfer(
            db,
            case_id=case_id,
            transfer_id=transfer_id,
            decision=payload.decision,
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
        raise_case_service_error(error)
