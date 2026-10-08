from types import SimpleNamespace

import pytest
from firebase_admin import auth

from app.cli import repair_emulator_user


def test_missing_emulator_user_is_recreated_with_database_uid(monkeypatch) -> None:
    user = SimpleNamespace(
        firebase_uid="database-firebase-uid",
        email="dentist@example.test",
        full_name="Demo Hekim",
        is_active=True,
    )
    firebase_app = object()
    created: dict[str, object] = {}
    monkeypatch.setattr(
        repair_emulator_user,
        "get_settings",
        lambda: SimpleNamespace(firebase_use_emulator=True),
    )
    monkeypatch.setattr(repair_emulator_user, "get_firebase_app", lambda: firebase_app)
    monkeypatch.setattr(repair_emulator_user, "prompt_password", lambda: "secure-password")

    def missing(*_args, **_kwargs):
        raise auth.UserNotFoundError("missing", "missing")

    monkeypatch.setattr(repair_emulator_user.auth, "get_user", missing)
    monkeypatch.setattr(repair_emulator_user.auth, "get_user_by_email", missing)
    monkeypatch.setattr(
        repair_emulator_user.auth,
        "create_user",
        lambda **kwargs: created.update(kwargs),
    )

    assert repair_emulator_user.repair_identity(user) == "restored"
    assert created == {
        "uid": user.firebase_uid,
        "email": user.email,
        "password": "secure-password",
        "display_name": user.full_name,
        "email_verified": False,
        "disabled": False,
        "app": firebase_app,
    }


def test_emulator_repair_is_disabled_for_real_firebase(monkeypatch) -> None:
    monkeypatch.setattr(
        repair_emulator_user,
        "get_settings",
        lambda: SimpleNamespace(firebase_use_emulator=False),
    )

    with pytest.raises(SystemExit, match="yalnızca Firebase Auth Emulator"):
        repair_emulator_user.repair_identity(SimpleNamespace())
