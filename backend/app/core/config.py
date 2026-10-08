from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CASE_WAIT_WARNING_HOURS = {
    "manager_review": 24,
    "manager_revision_requested": 48,
    "lab_design": 48,
    "dentist_review": 24,
    "design_revision_requested": 48,
    "ready_for_production": 24,
    "in_production": 48,
    "production_completed": 24,
    "shipped": 72,
    "return_review": 24,
    "reproduction_requested": 24,
    "rescan_requested": 72,
}


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
    upload_max_active_sessions_per_user: int = Field(default=3, ge=1, le=100)
    upload_max_reserved_bytes_per_user: int = Field(default=943_718_400, ge=1)
    mesh_validation_stale_minutes: int = 30
    mesh_validation_max_attempts: int = 3
    mesh_validation_max_faces: int = 5_500_000
    mesh_validation_max_ascii_bytes: int = 67_108_864
    mesh_validation_timeout_seconds: int = 600

    email_enabled: bool = True
    smtp_host: str = "127.0.0.1"
    smtp_port: int = Field(default=1025, ge=1, le=65_535)
    smtp_starttls: bool = False
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from_address: str = "dentalapp@example.test"
    email_from_name: str = "DentalApp"
    email_max_attempts: int = Field(default=5, ge=1, le=20)
    email_retry_base_seconds: int = Field(default=60, ge=1, le=3600)
    frontend_base_url: str = "http://localhost:5173"
    case_wait_warning_hours: dict[str, int] = Field(
        default_factory=lambda: dict(DEFAULT_CASE_WAIT_WARNING_HOURS)
    )

    patient_data_keys: dict[str, str] = Field(default_factory=dict)
    patient_data_active_key_id: str = "v1"
    patient_lookup_key: str | None = None

    firebase_project_id: str = "demo-dentalapp"
    firebase_credentials_path: Path | None = None
    firebase_use_emulator: bool = True
    firebase_auth_emulator_host: str = "127.0.0.1:9099"
    firebase_session_days: int = 5
    firebase_session_cookie_name: str = "dentalapp_session"
    csrf_cookie_name: str = "dentalapp_csrf"
    cookie_secure: bool = False

    @field_validator("storage_path")
    @classmethod
    def resolve_storage_path_from_backend(cls, value: Path) -> Path:
        if value.is_absolute():
            return value.resolve()
        return (BACKEND_DIR / value).resolve()

    @field_validator("case_wait_warning_hours")
    @classmethod
    def validate_wait_warning_hours(cls, value: dict[str, int]) -> dict[str, int]:
        unknown = set(value) - set(DEFAULT_CASE_WAIT_WARNING_HOURS)
        if unknown:
            raise ValueError("Bilinmeyen vaka durumları: " + ", ".join(sorted(unknown)))
        if any(hours <= 0 for hours in value.values()):
            raise ValueError("Bekleme uyarısı süreleri pozitif saat olmalıdır.")
        return value

    @model_validator(mode="after")
    def reject_unsafe_production_configuration(self) -> "Settings":
        if self.upload_max_reserved_bytes_per_user < self.upload_max_bytes:
            raise ValueError(
                "UPLOAD_MAX_RESERVED_BYTES_PER_USER, UPLOAD_MAX_BYTES değerinden "
                "küçük olamaz."
            )
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
        if self.patient_data_active_key_id not in self.patient_data_keys:
            unsafe.append("PATIENT_DATA_KEYS")
        if not self.patient_lookup_key:
            unsafe.append("PATIENT_LOOKUP_KEY")
        if unsafe:
            raise ValueError(
                "Üretim ortamı güvenli değil; şu ayarları düzeltin: " + ", ".join(unsafe)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
