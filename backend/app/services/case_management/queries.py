from typing import Literal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    CaseStatus,
    CaseStatusHistory,
    Clinic,
    DentalCase,
    RoleCode,
    User,
    UserClinicAssignment,
    UserRoleAssignment,
)
from app.services.case_management.access import (
    CASE_CREATE_ROLES,
    case_visibility_filter,
    clinic_ids_for_roles,
    require_case_visibility,
)
from app.services.case_management.patient_data import patient_code_lookup
from app.services.case_management.repository import CASE_LOAD_OPTIONS, load_case

CaseLifecycle = Literal["active", "completed", "closed"]
COMPLETED_CASE_STATUSES = (CaseStatus.DELIVERED, CaseStatus.REPRODUCTION_REQUESTED)
CLOSED_CASE_STATUSES = (CaseStatus.CANCELLED, CaseStatus.MANAGER_REJECTED)
TERMINAL_CASE_STATUSES = COMPLETED_CASE_STATUSES + CLOSED_CASE_STATUSES


def list_case_create_options(
    db: Session,
    *,
    actor: User,
) -> list[tuple[Clinic, list[User]]]:
    clinic_ids = clinic_ids_for_roles(actor, CASE_CREATE_ROLES)
    if not clinic_ids:
        return []

    clinics = list(
        db.scalars(
            select(Clinic)
            .where(Clinic.id.in_(clinic_ids), Clinic.is_active.is_(True))
            .order_by(Clinic.name, Clinic.id)
        ).all()
    )
    if not clinics:
        return []

    assignments = db.execute(
        select(UserClinicAssignment.clinic_id, User)
        .select_from(UserClinicAssignment)
        .join(User, User.id == UserClinicAssignment.user_id)
        .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
        .where(
            UserClinicAssignment.clinic_id.in_([clinic.id for clinic in clinics]),
            UserClinicAssignment.is_active.is_(True),
            UserRoleAssignment.role.in_({RoleCode.DENTIST, RoleCode.MANAGING_DENTIST}),
            UserRoleAssignment.is_active.is_(True),
            User.is_active.is_(True),
        )
        .order_by(User.full_name, User.id)
    ).all()

    dentists_by_clinic: dict[UUID, dict[UUID, User]] = {
        clinic.id: {} for clinic in clinics
    }
    for clinic_id, dentist in assignments:
        dentists_by_clinic[clinic_id][dentist.id] = dentist

    return [
        (clinic, list(dentists_by_clinic[clinic.id].values()))
        for clinic in clinics
    ]


def list_visible_cases(
    db: Session,
    *,
    actor: User,
    status: CaseStatus | None,
    lifecycle: CaseLifecycle | None,
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
    if lifecycle == "active":
        filters.append(DentalCase.status.not_in(TERMINAL_CASE_STATUSES))
    elif lifecycle == "completed":
        filters.append(DentalCase.status.in_(COMPLETED_CASE_STATUSES))
    elif lifecycle == "closed":
        filters.append(DentalCase.status.in_(CLOSED_CASE_STATUSES))
    if clinic_id is not None:
        filters.append(DentalCase.clinic_id == clinic_id)
    if responsible_dentist_user_id is not None:
        filters.append(DentalCase.responsible_dentist_user_id == responsible_dentist_user_id)
    if search is not None and (normalized_search := search.strip()):
        filters.append(
            or_(
                DentalCase.case_number.icontains(normalized_search, autoescape=True),
                DentalCase.patient_code_lookup == patient_code_lookup(normalized_search),
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
) -> tuple[DentalCase, list[CaseStatusHistory]]:
    case = load_case(db, case_id)
    require_case_visibility(actor, case)
    history = list(
        db.scalars(
            select(CaseStatusHistory)
            .where(CaseStatusHistory.case_id == case_id)
            .order_by(CaseStatusHistory.sequence_number)
        ).all()
    )
    return case, history
