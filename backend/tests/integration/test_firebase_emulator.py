from os import getenv
from uuid import uuid4

import pytest
import requests
from fastapi.testclient import TestClient
from firebase_admin import auth
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.firebase import get_firebase_app
from app.db.session import engine, get_db
from app.main import app
from app.models import AuditEvent, RoleCode, User, UserRoleAssignment
from app.services.firebase_identity import (
    create_identity,
    delete_identity,
    set_identity_disabled,
    update_identity_name,
)

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    getenv("RUN_FIREBASE_EMULATOR_TESTS") != "1",
    reason="Set RUN_FIREBASE_EMULATOR_TESTS=1 to run emulator integration tests.",
)
def test_firebase_identity_lifecycle() -> None:
    email = f"identity-{uuid4().hex}@example.invalid"
    firebase_uid = create_identity(
        email=email,
        full_name="Identity Test User",
        password="Identity-Test-Password-123!",
    )

    try:
        firebase_user = auth.get_user(firebase_uid, app=get_firebase_app())
        assert firebase_user.email == email
        assert firebase_user.display_name == "Identity Test User"
        assert firebase_user.disabled is False

        update_identity_name(firebase_uid, "Identity Test User Updated")
        set_identity_disabled(firebase_uid, disabled=True)

        firebase_user = auth.get_user(firebase_uid, app=get_firebase_app())
        assert firebase_user.display_name == "Identity Test User Updated"
        assert firebase_user.disabled is True
    finally:
        delete_identity(firebase_uid)

    with pytest.raises(auth.UserNotFoundError):
        auth.get_user(firebase_uid, app=get_firebase_app())


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

    try:
        with engine.connect() as connection:
            outer_transaction = connection.begin()
            test_session_factory = sessionmaker(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )

            def override_get_db():
                with test_session_factory() as session:
                    yield session

            try:
                with test_session_factory.begin() as session:
                    local_user = User(
                        firebase_uid=firebase_user.uid,
                        email=email,
                        full_name="Integration Test User",
                    )
                    session.add(local_user)
                    session.flush()
                    session.add(
                        UserRoleAssignment(
                            user_id=local_user.id,
                            role=RoleCode.SYSTEM_ADMIN,
                            clinic_id=None,
                        )
                    )

                app.dependency_overrides[get_db] = override_get_db

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

                with test_session_factory() as session:
                    actions = session.scalars(
                        select(AuditEvent.action)
                        .where(AuditEvent.actor_user_id == local_user.id)
                        .order_by(AuditEvent.created_at)
                    ).all()
                assert actions == ["auth.session_created", "auth.session_ended"]
            finally:
                app.dependency_overrides.pop(get_db, None)
                outer_transaction.rollback()
    finally:
        auth.delete_user(firebase_user.uid, app=get_firebase_app())
