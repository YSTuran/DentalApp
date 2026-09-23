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


@lru_cache
def get_settings() -> Settings:
    return Settings()
