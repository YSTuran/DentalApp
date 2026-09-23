from os import getenv
from uuid import uuid4

import pytest
import requests
from fastapi.testclient import TestClient
from firebase_admin import auth
from sqlalchemy import delete

from app.core.config import get_settings
from app.core.firebase import get_firebase_app
from app.db.session import SessionLocal
from app.main import app
from app.models import RoleCode, User, UserRoleAssignment

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    getenv("RUN_FIREBASE_EMULATOR_TESTS") != "1",
    reason="Set RUN_FIREBASE_EMULATOR_TESTS=1 to run emulator integration tests.",
)
def test_firebase_login_session_and_logout() -> None:
    settings = get_settings()
    suffix = uuid4().hex
    email = f"integration-{suffix}@example.invalid"
    password = "Integration-Test-Password-123!"
    firebase_user = auth.create_user(
        email=email,
        password=password,
        display_name="Integration Test User",
        app=get_firebase_app(),
    )
    local_user_id = None

    try:
        with SessionLocal.begin() as session:
            local_user = User(
                firebase_uid=firebase_user.uid,
                email=email,
                full_name="Integration Test User",
            )
            session.add(local_user)
            session.flush()
            local_user_id = local_user.id
            session.add(
                UserRoleAssignment(
                    user_id=local_user.id,
                    role=RoleCode.SYSTEM_ADMIN,
                    clinic_id=None,
                )
            )

        sign_in_response = requests.post(
            "http://"
            f"{settings.firebase_auth_emulator_host}"
            "/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=fake-api-key",
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=5,
        )
        sign_in_response.raise_for_status()
        id_token = sign_in_response.json()["idToken"]

        with TestClient(app) as client:
            csrf_response = client.get("/api/auth/csrf")
            csrf_token = csrf_response.json()["csrf_token"]
            session_response = client.post(
                "/api/auth/session",
                json={"id_token": id_token},
                headers={"X-CSRF-Token": csrf_token},
            )
            assert session_response.status_code == 200

            me_response = client.get("/api/auth/me")
            assert me_response.status_code == 200
            assert me_response.json()["global_roles"] == ["system_admin"]

            logout_response = client.post(
                "/api/auth/logout",
                headers={"X-CSRF-Token": csrf_token},
            )
            assert logout_response.status_code == 200
            assert "dentalapp_session" not in client.cookies
    finally:
        if local_user_id is not None:
            with SessionLocal.begin() as session:
                session.execute(
                    delete(UserRoleAssignment).where(UserRoleAssignment.user_id == local_user_id)
                )
                session.execute(delete(User).where(User.id == local_user_id))
        auth.delete_user(firebase_user.uid, app=get_firebase_app())
