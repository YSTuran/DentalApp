from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DentalApp API"
    app_env: str = "development"
    app_debug: bool = True
    demo_mode: bool = True
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://dentalapp_user:change-me@localhost:5432/dentalapp"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-this-before-real-use"
    cors_origins: list[str] = ["http://localhost:5173"]
    storage_path: Path = BACKEND_DIR.parent / "storage"
    upload_max_bytes: int = 314_572_800
    upload_chunk_max_bytes: int = 8_388_608
    upload_session_hours: int = 24
    mesh_validation_stale_minutes: int = 30
    mesh_validation_max_attempts: int = 3
    mesh_validation_max_faces: int = 5_500_000
    mesh_validation_timeout_seconds: int = 600

    firebase_project_id: str = "demo-dentalapp"
    firebase_credentials_path: Path | None = None
    firebase_use_emulator: bool = True
    firebase_auth_emulator_host: str = "127.0.0.1:9099"
    firebase_session_days: int = 5
    firebase_session_cookie_name: str = "dentalapp_session"
    csrf_cookie_name: str = "dentalapp_csrf"
    cookie_secure: bool = False

    @model_validator(mode="after")
    def reject_unsafe_production_configuration(self) -> "Settings":
        if self.app_env.lower() not in {"production", "prod"}:
            return self
        unsafe: list[str] = []
        if self.app_debug:
            unsafe.append("APP_DEBUG=false")
        if self.demo_mode:
            unsafe.append("DEMO_MODE=false")
        if self.firebase_use_emulator:
            unsafe.append("FIREBASE_USE_EMULATOR=false")
        if not self.cookie_secure:
            unsafe.append("COOKIE_SECURE=true")
        if self.secret_key == "change-this-before-real-use":
            unsafe.append("SECRET_KEY")
        if unsafe:
            raise ValueError(
                "Üretim ortamı güvenli değil; şu ayarları düzeltin: " + ", ".join(unsafe)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
