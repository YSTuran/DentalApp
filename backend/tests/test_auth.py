from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import auth as auth_dependencies
from app.api.dependencies.auth import get_optional_current_user
from app.api.routes import auth as auth_routes
from app.main import app
from app.models import RoleCode, User, UserRoleAssignment


def build_user() -> User:
    user = User(
        id=uuid4(),
        firebase_uid="firebase-test-user",
        email="test@example.invalid",
        full_name="Test User",
        is_active=True,
    )
    user.role_assignments = [
        UserRoleAssignment(
            id=uuid4(),
            user_id=user.id,
            role=RoleCode.SYSTEM_ADMIN,
            clinic_id=None,
            is_active=True,
        )
    ]
    return user


def test_csrf_endpoint_sets_cookie() -> None:
    with TestClient(app) as client:
        response = client.get("/api/auth/csrf")

    assert response.status_code == 200
    assert response.json()["csrf_token"]
    assert "dentalapp_csrf=" in response.headers["set-cookie"]


def test_session_rejects_missing_csrf() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/session",
            json={"id_token": "x" * 40},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "csrf_validation_failed"


def test_session_sets_http_only_cookie(monkeypatch) -> None:
    user = build_user()
    recorded_events = []
    monkeypatch.setattr(
        auth_routes,
        "create_session_cookie",
        lambda _token: ("signed-session-cookie", {"uid": user.firebase_uid}),
    )
    monkeypatch.setattr(
        auth_routes,
        "load_active_user_by_firebase_uid",
        lambda _db, _uid: user,
    )
    monkeypatch.setattr(
        auth_routes,
        "record_audit_event",
        lambda _db, **kwargs: recorded_events.append(kwargs),
    )

    with TestClient(app) as client:
        csrf_response = client.get("/api/auth/csrf")
        csrf_token = csrf_response.json()["csrf_token"]
        response = client.post(
            "/api/auth/session",
            json={"id_token": "x" * 40},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 200
    assert response.json()["global_roles"] == ["system_admin"]
    assert "dentalapp_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert recorded_events[0]["action"] == "auth.session_created"


def test_me_rejects_missing_session() -> None:
    with TestClient(app) as client:
        response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "authentication_required"


def test_me_returns_local_roles(monkeypatch) -> None:
    user = build_user()
    monkeypatch.setattr(
        auth_dependencies,
        "verify_session_cookie",
        lambda _cookie: {"uid": user.firebase_uid},
    )
    monkeypatch.setattr(
        auth_dependencies,
        "load_active_user_by_firebase_uid",
        lambda _db, _uid: user,
    )

    with TestClient(app, cookies={"dentalapp_session": "signed-cookie"}) as client:
        response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.json()["global_roles"] == ["system_admin"]


def test_logout_records_audit_for_authenticated_user(monkeypatch) -> None:
    user = build_user()
    recorded_events = []
    app.dependency_overrides[get_optional_current_user] = lambda: user
    monkeypatch.setattr(
        auth_routes,
        "record_audit_event",
        lambda _db, **kwargs: recorded_events.append(kwargs),
    )

    try:
        with TestClient(app) as client:
            csrf_response = client.get("/api/auth/csrf")
            response = client.post(
                "/api/auth/logout",
                headers={"X-CSRF-Token": csrf_response.json()["csrf_token"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert recorded_events[0]["action"] == "auth.session_ended"
