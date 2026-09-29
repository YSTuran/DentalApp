from uuid import UUID

from sqlalchemy import or_

from app.models import CaseStatus, DentalCase, RoleCode, User, UserRoleAssignment
from app.services.authorization import has_global_role
from app.services.case_management.exceptions import CaseAccessDeniedError

CLINIC_CASE_VIEW_ROLES = frozenset(
    {RoleCode.CLINIC_MANAGER, RoleCode.MANAGING_DENTIST, RoleCode.CLINIC_STAFF}
)
CASE_CREATE_ROLES = frozenset({RoleCode.MANAGING_DENTIST, RoleCode.DENTIST, RoleCode.CLINIC_STAFF})
LAB_VISIBLE_STATUSES = frozenset(
    {
        CaseStatus.LAB_DESIGN,
        CaseStatus.DENTIST_REVIEW,
        CaseStatus.DESIGN_REVISION_REQUESTED,
        CaseStatus.READY_FOR_PRODUCTION,
        CaseStatus.IN_PRODUCTION,
        CaseStatus.PRODUCTION_COMPLETED,
        CaseStatus.SHIPPED,
        CaseStatus.DELIVERED,
        CaseStatus.RETURN_REVIEW,
        CaseStatus.REPRODUCTION_REQUESTED,
    }
)


def active_assignments(actor: User) -> list[UserRoleAssignment]:
    return [assignment for assignment in actor.role_assignments if assignment.is_active]


def actor_roles(actor: User) -> frozenset[RoleCode]:
    return frozenset(assignment.role for assignment in active_assignments(actor))


def actor_clinic_ids(actor: User) -> frozenset[UUID]:
    return frozenset(
        assignment.clinic_id
        for assignment in active_assignments(actor)
        if assignment.clinic_id is not None
    )


def clinic_ids_for_roles(actor: User, roles: frozenset[RoleCode]) -> set[UUID]:
    return {
        assignment.clinic_id
        for assignment in active_assignments(actor)
        if assignment.clinic_id is not None and assignment.role in roles
    }


def has_role(actor: User, role: RoleCode) -> bool:
    return any(assignment.role == role for assignment in active_assignments(actor))


def case_visibility_filter(actor: User):
    if has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        return None

    conditions = []
    clinic_ids = clinic_ids_for_roles(actor, CLINIC_CASE_VIEW_ROLES)
    if clinic_ids:
        conditions.append(DentalCase.clinic_id.in_(clinic_ids))
    if has_role(actor, RoleCode.DENTIST):
        conditions.append(
            or_(
                DentalCase.created_by_user_id == actor.id,
                DentalCase.responsible_dentist_user_id == actor.id,
            )
        )
    if has_role(actor, RoleCode.TECHNICIAN):
        conditions.append(DentalCase.status.in_(LAB_VISIBLE_STATUSES))

    if not conditions:
        raise CaseAccessDeniedError
    return or_(*conditions)


def require_case_visibility(actor: User, case: DentalCase) -> None:
    visibility_filter = case_visibility_filter(actor)
    if visibility_filter is None:
        return

    clinic_access = case.clinic_id in clinic_ids_for_roles(actor, CLINIC_CASE_VIEW_ROLES)
    dentist_access = has_role(actor, RoleCode.DENTIST) and actor.id in {
        case.created_by_user_id,
        case.responsible_dentist_user_id,
    }
    technician_access = has_role(actor, RoleCode.TECHNICIAN) and (
        case.status in LAB_VISIBLE_STATUSES
    )
    if not (clinic_access or dentist_access or technician_access):
        raise CaseAccessDeniedError


def require_create_access(actor: User, clinic_id: UUID) -> None:
    if not any(
        assignment.clinic_id == clinic_id and assignment.role in CASE_CREATE_ROLES
        for assignment in active_assignments(actor)
    ):
        raise CaseAccessDeniedError


def can_view_patient_name(actor: User, case: DentalCase) -> bool:
    return has_global_role(actor, RoleCode.SYSTEM_ADMIN) or any(
        assignment.clinic_id == case.clinic_id for assignment in active_assignments(actor)
    )
