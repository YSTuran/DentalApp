from uuid import UUID

from app.models import RoleCode, User


def has_global_role(user: User, *roles: RoleCode) -> bool:
    allowed = set(roles)
    return any(
        assignment.is_active and assignment.clinic_id is None and assignment.role in allowed
        for assignment in user.role_assignments
    )


def has_any_role(user: User, *roles: RoleCode) -> bool:
    allowed = set(roles)
    return any(
        assignment.is_active and assignment.role in allowed for assignment in user.role_assignments
    )


def has_clinic_role(user: User, clinic_id: UUID, *roles: RoleCode) -> bool:
    allowed = set(roles)
    return any(
        assignment.is_active and assignment.clinic_id == clinic_id and assignment.role in allowed
        for assignment in user.role_assignments
    )


def can_access_clinic(user: User, clinic_id: UUID) -> bool:
    return has_global_role(user, RoleCode.SYSTEM_ADMIN) or any(
        assignment.is_active and assignment.clinic_id == clinic_id
        for assignment in user.role_assignments
    )
