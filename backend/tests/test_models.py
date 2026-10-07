from app.models import Base, RoleCode


def test_identity_tables_are_registered() -> None:
    assert {
        "audit_events",
        "case_wait_alerts",
        "clinics",
        "email_outbox",
        "users",
        "user_clinic_assignments",
        "user_role_assignments",
    }.issubset(Base.metadata.tables)


def test_only_system_admin_and_technician_are_global_roles() -> None:
    global_roles = {role for role in RoleCode if role.is_global}

    assert global_roles == {RoleCode.SYSTEM_ADMIN, RoleCode.TECHNICIAN}


def test_role_and_clinic_assignments_are_separate() -> None:
    table = Base.metadata.tables["user_role_assignments"]

    assert "clinic_id" not in table.columns
    assert "user_clinic_assignments" in Base.metadata.tables


def test_patient_identity_uses_only_encrypted_case_columns() -> None:
    columns = Base.metadata.tables["cases"].columns

    assert {"patient_code_encrypted", "patient_code_lookup", "patient_name_encrypted"} <= {
        column.name for column in columns
    }
    assert "patient_code" not in columns
    assert "patient_name" not in columns
