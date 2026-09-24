from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.main import app
from app.models import RoleCode, User, UserRoleAssignment


class EmptyScalars:
    def all(self) -> list[object]:
        return []


class EmptyAuditSession:
    def scalar(self, _statement) -> int:
        return 0

    def scalars(self, _statement) -> EmptyScalars:
        return EmptyScalars()


def build_user(role: RoleCode, clinic_id=None) -> User:
    user = User(
        id=uuid4(),
        firebase_uid=uuid4().hex,
        email="audit-api@example.invalid",
        full_name="Audit API User",
    )
    user.role_assignments = [
        UserRoleAssignment(
            id=uuid4(),
            user_id=user.id,
            role=role,
            clinic_id=clinic_id,
            is_active=True,
        )
    ]
    return user


def test_audit_event_list_is_available_to_system_admin() -> None:
    app.dependency_overrides[get_current_user] = lambda: build_user(RoleCode.SYSTEM_ADMIN)
    app.dependency_overrides[get_db] = lambda: EmptyAuditSession()

    try:
        with TestClient(app) as client:
            response = client.get("/api/audit-events")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_audit_event_list_rejects_non_admin() -> None:
    app.dependency_overrides[get_current_user] = lambda: build_user(
        RoleCode.DENTIST,
        uuid4(),
    )
    app.dependency_overrides[get_db] = lambda: EmptyAuditSession()

    try:
        with TestClient(app) as client:
            response = client.get("/api/audit-events")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_permissions"
