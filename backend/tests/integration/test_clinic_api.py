from collections.abc import Generator
from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.db.session import engine, get_db
from app.main import app
from app.models import AuditEvent, Clinic, RoleCode, User, UserRoleAssignment
from app.services import clinics as clinic_service

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session]]:
    with engine.connect() as connection:
        outer_transaction = connection.begin()
        factory = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        def override_get_db():
            with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            yield factory
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            outer_transaction.rollback()


def create_clinic_record(factory: sessionmaker[Session], code: str) -> Clinic:
    with factory.begin() as session:
        clinic = Clinic(code=code, name=f"Clinic {code}")
        session.add(clinic)
        session.flush()
    return clinic


def create_user(
    factory: sessionmaker[Session],
    role: RoleCode,
    clinic_id=None,
) -> User:
    with factory.begin() as session:
        user = User(
            firebase_uid=uuid4().hex,
            email=f"{uuid4().hex}@example.invalid",
            full_name="Clinic API Test",
        )
        user.role_assignments = [UserRoleAssignment(role=role, clinic_id=clinic_id, is_active=True)]
        session.add(user)
        session.flush()
    return user


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/auth/csrf")
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_system_admin_can_manage_clinic_lifecycle_and_writes_audit(
    session_factory: sessionmaker[Session],
) -> None:
    admin = create_user(session_factory, RoleCode.SYSTEM_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin
    code = f"IST-{uuid4().hex[:8]}"

    with TestClient(app) as client:
        headers = csrf_headers(client)
        create_response = client.post(
            "/api/clinics",
            headers=headers,
            json={
                "code": code.lower(),
                "name": "  DentalApp İstanbul  ",
                "address": "Kadıköy",
                "reason": "Yeni demo şubesi",
            },
        )
        assert create_response.status_code == 201
        clinic = create_response.json()
        clinic_id = clinic["id"]
        assert clinic["code"] == code.upper()
        assert clinic["name"] == "DentalApp İstanbul"

        duplicate_response = client.post(
            "/api/clinics",
            headers=headers,
            json={"code": code.lower(), "name": "Duplicate"},
        )
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"] == "clinic_code_exists"

        update_response = client.patch(
            f"/api/clinics/{clinic_id}",
            headers=headers,
            json={"name": "DentalApp Kadıköy", "reason": "Şube adı düzeltildi"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "DentalApp Kadıköy"

        missing_reason = client.post(
            f"/api/clinics/{clinic_id}/deactivate",
            headers=headers,
            json={},
        )
        assert missing_reason.status_code == 422

        deactivate_response = client.post(
            f"/api/clinics/{clinic_id}/deactivate",
            headers=headers,
            json={"reason": "Şube geçici olarak kapatıldı"},
        )
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["is_active"] is False

        reactivate_response = client.post(
            f"/api/clinics/{clinic_id}/reactivate",
            headers=headers,
            json={"reason": "Şube yeniden açıldı"},
        )
        assert reactivate_response.status_code == 200
        assert reactivate_response.json()["is_active"] is True

        list_response = client.get(f"/api/clinics?search={code}&is_active=true")
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()["items"]] == [clinic_id]

        delete_response = client.delete(f"/api/clinics/{clinic_id}", headers=headers)
        assert delete_response.status_code == 405

    with session_factory() as session:
        events = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == clinic_id)
            .order_by(AuditEvent.created_at, AuditEvent.action)
        ).all()

    assert {event.action for event in events} == {
        "clinic.created",
        "clinic.updated",
        "clinic.deactivated",
        "clinic.reactivated",
    }
    update_event = next(event for event in events if event.action == "clinic.updated")
    assert update_event.before_data == {"name": "DentalApp İstanbul"}
    assert update_event.after_data == {"name": "DentalApp Kadıköy"}
    assert update_event.reason == "Şube adı düzeltildi"


def test_clinic_manager_only_sees_assigned_clinic(
    session_factory: sessionmaker[Session],
) -> None:
    own_clinic = create_clinic_record(session_factory, f"OWN-{uuid4().hex[:8]}")
    other_clinic = create_clinic_record(session_factory, f"OTHER-{uuid4().hex[:8]}")
    manager = create_user(session_factory, RoleCode.CLINIC_MANAGER, own_clinic.id)
    app.dependency_overrides[get_current_user] = lambda: manager

    with TestClient(app) as client:
        list_response = client.get("/api/clinics")
        own_response = client.get(f"/api/clinics/{own_clinic.id}")
        other_response = client.get(f"/api/clinics/{other_clinic.id}")
        create_response = client.post(
            "/api/clinics",
            headers=csrf_headers(client),
            json={"code": f"NO-{uuid4().hex[:8]}", "name": "Not Allowed"},
        )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [str(own_clinic.id)]
    assert own_response.status_code == 200
    assert other_response.status_code == 403
    assert other_response.json()["detail"] == "clinic_role_required"
    assert create_response.status_code == 403
    assert create_response.json()["detail"] == "insufficient_permissions"


def test_dentist_cannot_access_clinic_management(
    session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic_record(session_factory, f"DEN-{uuid4().hex[:8]}")
    dentist = create_user(session_factory, RoleCode.DENTIST, clinic.id)
    app.dependency_overrides[get_current_user] = lambda: dentist

    with TestClient(app) as client:
        list_response = client.get("/api/clinics")
        detail_response = client.get(f"/api/clinics/{clinic.id}")

    assert list_response.status_code == 403
    assert detail_response.status_code == 403


def test_clinic_creation_rolls_back_when_audit_fails(
    session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    admin = create_user(session_factory, RoleCode.SYSTEM_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin
    code = f"ROLLBACK-{uuid4().hex[:8]}"

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(clinic_service, "record_audit_event", fail_audit)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/clinics",
            headers=csrf_headers(client),
            json={"code": code, "name": "Must Roll Back"},
        )

    assert response.status_code == 500
    with session_factory() as session:
        clinic_count = session.scalar(
            select(func.count()).select_from(Clinic).where(Clinic.code == code)
        )
    assert clinic_count == 0
