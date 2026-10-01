from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import CaseStatus, CaseStatusHistory, DentalCase, User
from app.services.case_management.access import case_visibility_filter, require_case_visibility
from app.services.case_management.repository import CASE_LOAD_OPTIONS, load_case


def list_visible_cases(
    db: Session,
    *,
    actor: User,
    status: CaseStatus | None,
    clinic_id: UUID | None,
    responsible_dentist_user_id: UUID | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[DentalCase], int]:
    filters = []
    visibility_filter = case_visibility_filter(actor)
    if visibility_filter is not None:
        filters.append(visibility_filter)
    if status is not None:
        filters.append(DentalCase.status == status)
    if clinic_id is not None:
        filters.append(DentalCase.clinic_id == clinic_id)
    if responsible_dentist_user_id is not None:
        filters.append(DentalCase.responsible_dentist_user_id == responsible_dentist_user_id)
    if search is not None and (normalized_search := search.strip()):
        filters.append(
            or_(
                DentalCase.case_number.icontains(normalized_search, autoescape=True),
                DentalCase.patient_code.icontains(normalized_search, autoescape=True),
            )
        )

    total = db.scalar(select(func.count()).select_from(DentalCase).where(*filters)) or 0
    cases = db.scalars(
        select(DentalCase)
        .where(*filters)
        .options(*CASE_LOAD_OPTIONS)
        .order_by(DentalCase.created_at.desc(), DentalCase.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(cases), total


def get_visible_case(db: Session, *, actor: User, case_id: UUID) -> DentalCase:
    case = load_case(db, case_id)
    require_case_visibility(actor, case)
    return case


def list_case_history(
    db: Session,
    *,
    actor: User,
    case_id: UUID,
) -> list[CaseStatusHistory]:
    case = load_case(db, case_id)
    require_case_visibility(actor, case)
    return list(
        db.scalars(
            select(CaseStatusHistory)
            .where(CaseStatusHistory.case_id == case_id)
            .order_by(CaseStatusHistory.sequence_number)
        ).all()
    )
