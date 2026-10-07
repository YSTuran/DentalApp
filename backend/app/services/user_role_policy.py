from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Clinic, RoleCode, UserRoleAssignment
from app.services.user_errors import UserConflictError, UserValidationError


def validate_initial_clinics(
    db: Session,
    *,
    role: RoleCode,
    clinic_ids: list[UUID],
) -> list[Clinic]:
    unique_ids = list(dict.fromkeys(clinic_ids))
    if role.is_global:
        if unique_ids:
            raise UserValidationError("global_role_cannot_have_clinic")
        return []
    if not unique_ids:
        raise UserValidationError("clinic_role_requires_clinic")
    clinics = list(db.scalars(select(Clinic).where(Clinic.id.in_(unique_ids))).all())
    if len(clinics) != len(unique_ids):
        raise UserValidationError("clinic_not_found")
    if any(not clinic.is_active for clinic in clinics):
        raise UserConflictError("clinic_inactive")
    return clinics


def reject_system_admin_assignment(role: RoleCode) -> None:
    if role == RoleCode.SYSTEM_ADMIN:
        raise UserValidationError("system_admin_assignment_not_allowed")


def validate_role_compatibility(
    db: Session,
    *,
    user_id: UUID,
    role: RoleCode,
    exclude_assignment_id: UUID | None = None,
) -> None:
    statement = select(UserRoleAssignment.role).where(
        UserRoleAssignment.user_id == user_id,
        UserRoleAssignment.is_active.is_(True),
    )
    if exclude_assignment_id is not None:
        statement = statement.where(UserRoleAssignment.id != exclude_assignment_id)
    active_roles = set(db.scalars(statement).all())
    if active_roles and active_roles != {role}:
        raise UserValidationError("conflicting_active_role")
