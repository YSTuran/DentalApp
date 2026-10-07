from uuid import UUID

from sqlalchemy import exists, or_, select

from app.models import (
    CaseStatus,
    CaseTransfer,
    CaseTransferStatus,
    DentalCase,
    RoleCode,
    User,
)
from app.services.authorization import has_any_role, has_clinic_role, has_global_role
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


def active_assignments(actor: User):
    return [assignment for assignment in actor.role_assignments if assignment.is_active]


def actor_role_assignments(actor: User) -> frozenset[tuple[RoleCode, UUID | None]]:
    roles = [assignment.role for assignment in active_assignments(actor)]
    clinic_ids = {
        assignment.clinic_id
        for assignment in actor.clinic_assignments
        if assignment.is_active
    }
    scoped = {(role, clinic_id) for role in roles for clinic_id in clinic_ids}
    scoped.update(
        (role, None)
        for role in roles
        if role in {RoleCode.SYSTEM_ADMIN, RoleCode.TECHNICIAN}
    )
    return frozenset(scoped)


def clinic_ids_for_roles(actor: User, roles: frozenset[RoleCode]) -> set[UUID]:
    if not any(assignment.role in roles for assignment in active_assignments(actor)):
        return set()
    return {
        assignment.clinic_id
        for assignment in actor.clinic_assignments
        if assignment.is_active
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
                exists(
                    select(CaseTransfer.id).where(
                        CaseTransfer.case_id == DentalCase.id,
                        CaseTransfer.to_dentist_user_id == actor.id,
                        CaseTransfer.status == CaseTransferStatus.PENDING,
                    )
                ),
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
    pending_transfer_access = has_role(actor, RoleCode.DENTIST) and any(
        transfer.to_dentist_user_id == actor.id
        and transfer.status == CaseTransferStatus.PENDING
        for transfer in case.transfers
    )
    technician_access = has_role(actor, RoleCode.TECHNICIAN) and (
        case.status in LAB_VISIBLE_STATUSES
    )
    if not (clinic_access or dentist_access or pending_transfer_access or technician_access):
        raise CaseAccessDeniedError


def require_create_access(actor: User, clinic_id: UUID) -> None:
    if not has_clinic_role(actor, clinic_id, *CASE_CREATE_ROLES):
        raise CaseAccessDeniedError


def can_view_patient_name(actor: User, case: DentalCase) -> bool:
    if has_any_role(actor, RoleCode.DENTIST, RoleCode.MANAGING_DENTIST) and actor.id in {
        case.created_by_user_id,
        case.responsible_dentist_user_id,
    }:
        return True
    return has_clinic_role(
        actor,
        case.clinic_id,
        RoleCode.CLINIC_MANAGER,
        RoleCode.MANAGING_DENTIST,
        RoleCode.CLINIC_STAFF,
    )
