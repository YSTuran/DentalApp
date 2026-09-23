from app.models import Base, RoleCode


def test_identity_tables_are_registered() -> None:
    assert {"clinics", "users", "user_role_assignments"}.issubset(Base.metadata.tables)


def test_only_system_admin_and_technician_are_global_roles() -> None:
    global_roles = {role for role in RoleCode if role.is_global}

    assert global_roles == {RoleCode.SYSTEM_ADMIN, RoleCode.TECHNICIAN}


def test_role_assignment_has_scope_constraint() -> None:
    table = Base.metadata.tables["user_role_assignments"]
    constraint_names = {constraint.name for constraint in table.constraints}

    assert "ck_user_role_assignments_role_scope" in constraint_names
