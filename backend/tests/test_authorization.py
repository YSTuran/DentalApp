from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.dependencies.authorization import (
    require_clinic_access,
    require_clinic_roles,
    require_system_admin,
)
from app.models import RoleCode, User, UserRoleAssignment
from app.services.authorization import (
    can_access_clinic,
    has_any_role,
    has_clinic_role,
    has_global_role,
)


def build_user(*assignments: tuple[RoleCode, UUID | None, bool]) -> User:
    user = User(
        id=uuid4(),
        firebase_uid=uuid4().hex,
        email="role-test@example.invalid",
        full_name="Role Test",
    )
    user.role_assignments = [
        UserRoleAssignment(
            id=uuid4(),
            user_id=user.id,
            role=role,
            clinic_id=clinic_id,
            is_active=is_active,
        )
        for role, clinic_id, is_active in assignments
    ]
    return user


def test_role_helpers_respect_scope_and_inactive_assignments() -> None:
    clinic_id = uuid4()
    other_clinic_id = uuid4()
    user = build_user(
        (RoleCode.DENTIST, clinic_id, True),
        (RoleCode.CLINIC_MANAGER, other_clinic_id, False),
    )

    assert has_any_role(user, RoleCode.DENTIST)
    assert has_clinic_role(user, clinic_id, RoleCode.DENTIST)
    assert not has_clinic_role(user, other_clinic_id, RoleCode.DENTIST)
    assert not has_any_role(user, RoleCode.CLINIC_MANAGER)
    assert not has_global_role(user, RoleCode.DENTIST)


def test_system_admin_can_access_every_clinic() -> None:
    user = build_user((RoleCode.SYSTEM_ADMIN, None, True))

    assert can_access_clinic(user, uuid4())
    assert require_system_admin(user) is user


def test_clinic_role_does_not_implicitly_allow_system_admin() -> None:
    user = build_user((RoleCode.SYSTEM_ADMIN, None, True))
    dependency = require_clinic_roles(RoleCode.MANAGING_DENTIST)

    with pytest.raises(HTTPException) as error:
        dependency(uuid4(), user)

    assert error.value.status_code == 403
    assert error.value.detail == "clinic_role_required"


def test_clinic_role_can_explicitly_allow_system_admin() -> None:
    user = build_user((RoleCode.SYSTEM_ADMIN, None, True))
    dependency = require_clinic_roles(RoleCode.CLINIC_MANAGER, allow_system_admin=True)

    assert dependency(uuid4(), user) is user


def test_clinic_access_rejects_user_from_another_clinic() -> None:
    user = build_user((RoleCode.DENTIST, uuid4(), True))

    with pytest.raises(HTTPException) as error:
        require_clinic_access(uuid4(), user)

    assert error.value.status_code == 403
    assert error.value.detail == "clinic_access_denied"
