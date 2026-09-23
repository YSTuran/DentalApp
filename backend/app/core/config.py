from functools import lru_cache
from pathlib import Path

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

    firebase_project_id: str = "demo-dentalapp"
    firebase_credentials_path: Path | None = None
    firebase_use_emulator: bool = True
    firebase_auth_emulator_host: str = "127.0.0.1:9099"
    firebase_session_days: int = 5
    firebase_session_cookie_name: str = "dentalapp_session"
    csrf_cookie_name: str = "dentalapp_csrf"
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
