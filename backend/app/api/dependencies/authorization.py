from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.api.dependencies.auth import get_current_user
from app.models import RoleCode, User
from app.services.authorization import (
    can_access_clinic,
    has_any_role,
    has_clinic_role,
    has_global_role,
)

CurrentUser = Annotated[User, Depends(get_current_user)]


def _deny(detail: str = "insufficient_permissions") -> None:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_system_admin(user: CurrentUser) -> User:
    if not has_global_role(user, RoleCode.SYSTEM_ADMIN):
        _deny()
    return user


def require_global_roles(*roles: RoleCode) -> Callable[..., User]:
    if not roles:
        raise ValueError("En az bir global rol belirtilmelidir.")

    def dependency(user: CurrentUser) -> User:
        if not has_global_role(user, *roles):
            _deny()
        return user

    return dependency


def require_any_role(*roles: RoleCode) -> Callable[..., User]:
    if not roles:
        raise ValueError("En az bir rol belirtilmelidir.")

    def dependency(user: CurrentUser) -> User:
        if not has_any_role(user, *roles):
            _deny()
        return user

    return dependency


def require_clinic_access(clinic_id: UUID, user: CurrentUser) -> User:
    if not can_access_clinic(user, clinic_id):
        _deny("clinic_access_denied")
    return user


def require_clinic_roles(
    *roles: RoleCode,
    allow_system_admin: bool = False,
) -> Callable[..., User]:
    if not roles:
        raise ValueError("En az bir klinik rolü belirtilmelidir.")

    def dependency(clinic_id: UUID, user: CurrentUser) -> User:
        is_allowed = has_clinic_role(user, clinic_id, *roles)
        if allow_system_admin:
            is_allowed = is_allowed or has_global_role(user, RoleCode.SYSTEM_ADMIN)
        if not is_allowed:
            _deny("clinic_role_required")
        return user

    return dependency
