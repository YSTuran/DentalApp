from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.cases import case_access
from app.api.routes.case_errors import raise_case_service_error
from app.db.session import get_db
from app.models import User
from app.schemas.report import CaseReportResponse
from app.services.case_management.exceptions import CaseAccessDeniedError, CaseValidationError
from app.services.reports import generate_case_report

router = APIRouter()


@router.get("/cases", response_model=CaseReportResponse)
def case_report(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    clinic_id: UUID | None = None,
) -> CaseReportResponse:
    try:
        return generate_case_report(
            db,
            actor=actor,
            date_from=date_from,
            date_to=date_to,
            clinic_id=clinic_id,
        )
    except (CaseAccessDeniedError, CaseValidationError) as error:
        raise_case_service_error(error)
