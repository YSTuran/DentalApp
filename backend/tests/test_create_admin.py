from types import SimpleNamespace

import pytest
from firebase_admin import auth

from app.cli import create_admin


def test_restore_emulator_admin_recreates_user_with_same_uid(monkeypatch) -> None:
    user = SimpleNamespace(
        firebase_uid="firebase-admin-uid",
        email="admin@example.test",
        full_name="Demo Admin",
    )
    firebase_app = object()
    created_user: dict[str, object] = {}

    monkeypatch.setattr(
        create_admin,
        "get_settings",
        lambda: SimpleNamespace(firebase_use_emulator=True),
    )
    monkeypatch.setattr(create_admin, "get_firebase_app", lambda: firebase_app)
    monkeypatch.setattr(create_admin, "prompt_password", lambda: "strong-test-password")

    def missing_user(*_args, **_kwargs):
        raise auth.UserNotFoundError("missing", "missing")

    monkeypatch.setattr(create_admin.auth, "get_user", missing_user)
    monkeypatch.setattr(create_admin.auth, "get_user_by_email", missing_user)
    monkeypatch.setattr(
        create_admin.auth,
        "create_user",
        lambda **kwargs: created_user.update(kwargs),
    )

    create_admin.restore_emulator_admin(user)

    assert created_user == {
        "uid": user.firebase_uid,
        "email": user.email,
        "password": "strong-test-password",
        "display_name": user.full_name,
        "email_verified": False,
        "app": firebase_app,
    }


def test_restore_emulator_admin_is_disabled_for_real_firebase(monkeypatch) -> None:
    user = SimpleNamespace(
        firebase_uid="firebase-admin-uid",
        email="admin@example.test",
        full_name="Demo Admin",
    )
    monkeypatch.setattr(
        create_admin,
        "get_settings",
        lambda: SimpleNamespace(firebase_use_emulator=False),
    )

    with pytest.raises(SystemExit, match="Gerçek Firebase"):
        create_admin.restore_emulator_admin(user)
