import json
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
from app.services import users as user_service

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


def create_clinic(factory: sessionmaker[Session], prefix: str) -> Clinic:
    with factory.begin() as session:
        clinic = Clinic(code=f"{prefix}-{uuid4().hex[:8]}", name=f"{prefix} Clinic")
        session.add(clinic)
        session.flush()
    return clinic


def create_user(
    factory: sessionmaker[Session],
    *assignments: tuple[RoleCode, object | None],
    full_name: str = "User API Test",
) -> User:
    with factory.begin() as session:
        user = User(
            firebase_uid=uuid4().hex,
            email=f"{uuid4().hex}@example.invalid",
            full_name=full_name,
        )
        user.role_assignments = [
            UserRoleAssignment(role=role, clinic_id=clinic_id, is_active=True)
            for role, clinic_id in assignments
        ]
        session.add(user)
        session.flush()
    return user


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/auth/csrf")
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_system_admin_can_manage_user_roles_and_status_with_audit(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clinic = create_clinic(session_factory, "USER")
    admin = create_user(session_factory, (RoleCode.SYSTEM_ADMIN, None))
    app.dependency_overrides[get_current_user] = lambda: admin

    firebase_calls: list[tuple] = []

    def fake_create_identity(*, email: str, full_name: str, password: str) -> str:
        firebase_calls.append(("create", email, full_name, password))
        return f"firebase-{uuid4().hex}"

    monkeypatch.setattr(user_service, "create_identity", fake_create_identity)
    monkeypatch.setattr(
        user_service,
        "update_identity_name",
        lambda uid, name: firebase_calls.append(("rename", uid, name)),
    )
    monkeypatch.setattr(
        user_service,
        "set_identity_disabled",
        lambda uid, *, disabled: firebase_calls.append(("disable", uid, disabled)),
    )

    email = f"doctor-{uuid4().hex}@example.invalid"
    with TestClient(app) as client:
        headers = csrf_headers(client)
        create_response = client.post(
            "/api/users",
            headers=headers,
            json={
                "email": email,
                "full_name": "  Demo Hekim  ",
                "role": "dentist",
                "clinic_id": str(clinic.id),
                "reason": "Demo hesabı açıldı",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        user_id = created["user"]["id"]
        temporary_password = created["temporary_password"]
        assert created["user"]["full_name"] == "Demo Hekim"
        assert len(temporary_password) == 20
        assert firebase_calls[0] == ("create", email, "Demo Hekim", temporary_password)

        update_response = client.patch(
            f"/api/users/{user_id}",
            headers=headers,
            json={"full_name": "Demo Hekim Güncel", "reason": "Soyadı düzeltildi"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == "Demo Hekim Güncel"

        role_response = client.post(
            f"/api/users/{user_id}/roles",
            headers=headers,
            json={
                "role": "managing_dentist",
                "clinic_id": str(clinic.id),
                "reason": "Yönetici hekim görevi verildi",
            },
        )
        assert role_response.status_code == 201
        role_id = role_response.json()["id"]

        deactivate_role_response = client.post(
            f"/api/users/{user_id}/roles/{role_id}/deactivate",
            headers=headers,
            json={"reason": "Görev sona erdi"},
        )
        assert deactivate_role_response.status_code == 200
        assert deactivate_role_response.json()["is_active"] is False

        deactivate_response = client.post(
            f"/api/users/{user_id}/deactivate",
            headers=headers,
            json={"reason": "Kullanıcı klinikten ayrıldı"},
        )
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["is_active"] is False

        reactivate_response = client.post(
            f"/api/users/{user_id}/reactivate",
            headers=headers,
            json={"reason": "Kullanıcı geri döndü"},
        )
        assert reactivate_response.status_code == 200
        assert reactivate_response.json()["is_active"] is True

        delete_response = client.delete(f"/api/users/{user_id}", headers=headers)
        assert delete_response.status_code == 405

    with session_factory() as session:
        events = session.scalars(
            select(AuditEvent).where(
                (AuditEvent.entity_id == user_id)
                | (AuditEvent.context_data["user_id"].astext == user_id)
            )
        ).all()

    assert {
        "user.created",
        "user.updated",
        "user.deactivated",
        "user.reactivated",
        "user.role_deactivated",
    }.issubset({event.action for event in events})
    serialized_events = json.dumps(
        [
            {
                "before": event.before_data,
                "after": event.after_data,
                "context": event.context_data,
                "reason": event.reason,
            }
            for event in events
        ],
        default=str,
    )
    assert temporary_password not in serialized_events
    assert any(call[0:1] == ("rename",) for call in firebase_calls)
    assert [call[2] for call in firebase_calls if call[0] == "disable"] == [True, False]


def test_clinic_manager_only_sees_own_clinic_doctors(
    session_factory: sessionmaker[Session],
) -> None:
    own_clinic = create_clinic(session_factory, "OWN")
    other_clinic = create_clinic(session_factory, "OTHER")
    manager = create_user(
        session_factory,
        (RoleCode.CLINIC_MANAGER, own_clinic.id),
        full_name="Clinic Manager",
    )
    own_dentist = create_user(
        session_factory,
        (RoleCode.DENTIST, own_clinic.id),
        (RoleCode.MANAGING_DENTIST, other_clinic.id),
        (RoleCode.CLINIC_STAFF, own_clinic.id),
        full_name="Own Dentist",
    )
    own_managing_dentist = create_user(
        session_factory,
        (RoleCode.MANAGING_DENTIST, own_clinic.id),
        full_name="Own Managing Dentist",
    )
    own_staff = create_user(
        session_factory,
        (RoleCode.CLINIC_STAFF, own_clinic.id),
        full_name="Own Staff",
    )
    other_dentist = create_user(
        session_factory,
        (RoleCode.DENTIST, other_clinic.id),
        full_name="Other Dentist",
    )
    app.dependency_overrides[get_current_user] = lambda: manager

    with TestClient(app) as client:
        list_response = client.get("/api/users")
        own_detail = client.get(f"/api/users/{own_dentist.id}")
        staff_detail = client.get(f"/api/users/{own_staff.id}")
        other_detail = client.get(f"/api/users/{other_dentist.id}")
        forbidden_filter = client.get("/api/users?role=clinic_staff")

    assert list_response.status_code == 200
    assert {item["id"] for item in list_response.json()["items"]} == {
        str(own_dentist.id),
        str(own_managing_dentist.id),
    }
    assert own_detail.status_code == 200
    visible_assignments = own_detail.json()["role_assignments"]
    assert len(visible_assignments) == 1
    assert visible_assignments[0]["role"] == "dentist"
    assert visible_assignments[0]["clinic_id"] == str(own_clinic.id)
    assert staff_detail.status_code == 403
    assert other_detail.status_code == 403
    assert forbidden_filter.status_code == 403


def test_create_user_rolls_back_database_and_firebase_when_audit_fails(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clinic = create_clinic(session_factory, "ROLLBACK")
    admin = create_user(session_factory, (RoleCode.SYSTEM_ADMIN, None))
    app.dependency_overrides[get_current_user] = lambda: admin
    firebase_uid = f"firebase-{uuid4().hex}"
    deleted_uids: list[str] = []
    email = f"rollback-{uuid4().hex}@example.invalid"

    monkeypatch.setattr(user_service, "create_identity", lambda **_kwargs: firebase_uid)
    monkeypatch.setattr(user_service, "delete_identity", deleted_uids.append)
    monkeypatch.setattr(
        user_service,
        "record_audit_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("audit unavailable")),
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/users",
            headers=csrf_headers(client),
            json={
                "email": email,
                "full_name": "Must Roll Back",
                "role": "dentist",
                "clinic_id": str(clinic.id),
            },
        )

    assert response.status_code == 500
    assert deleted_uids == [firebase_uid]
    with session_factory() as session:
        count = session.scalar(select(func.count()).select_from(User).where(User.email == email))
    assert count == 0


def test_user_creation_validates_role_scope_before_calling_firebase(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = create_user(session_factory, (RoleCode.SYSTEM_ADMIN, None))
    app.dependency_overrides[get_current_user] = lambda: admin
    firebase_called = False

    def fake_create_identity(**_kwargs):
        nonlocal firebase_called
        firebase_called = True
        return uuid4().hex

    monkeypatch.setattr(user_service, "create_identity", fake_create_identity)

    with TestClient(app) as client:
        response = client.post(
            "/api/users",
            headers=csrf_headers(client),
            json={
                "email": f"invalid-{uuid4().hex}@example.invalid",
                "full_name": "Invalid Scope",
                "role": "dentist",
                "clinic_id": None,
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "clinic_role_requires_clinic"
    assert firebase_called is False
