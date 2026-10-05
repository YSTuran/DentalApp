from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import BACKEND_DIR, Settings


def test_relative_storage_path_is_resolved_from_backend_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    settings = Settings(storage_path=Path("../storage"))

    assert settings.storage_path == (BACKEND_DIR / "../storage").resolve()


def test_production_rejects_development_security_flags() -> None:
    with pytest.raises(ValidationError, match="Üretim ortamı güvenli değil"):
        Settings(
            app_env="production",
            app_debug=True,
            demo_mode=True,
            firebase_use_emulator=True,
            cookie_secure=False,
            secret_key="change-this-before-real-use",
        )


def test_production_accepts_explicit_safe_flags() -> None:
    settings = Settings(
        app_env="production",
        app_debug=False,
        demo_mode=False,
        firebase_use_emulator=False,
        cookie_secure=True,
        secret_key="production-secret-is-injected-at-runtime",
    )

    assert settings.app_env == "production"
