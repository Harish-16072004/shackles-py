"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to the project root (two levels up from src/shackles/config.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "Shackles Symposium"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    active_year: int = 2026

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+asyncpg://shackles:shackles_dev@localhost:5432/shackles",
        description="Async SQLAlchemy database URL",
    )
    database_echo: bool = False

    # ---- Redis / Valkey ----
    redis_url: str = "redis://localhost:6379"

    # ---- Auth ----
    secret_key: str = "dev-only-secret-key-change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ---- Storage ----
    storage_provider: Literal["local", "gcs", "s3", "azure"] = "local"
    storage_local_root: str = "storage"

    # ---- Email ----
    email_from: str = "Shackles <noreply@shackles.local>"
    resend_api_key: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None

    # ---- Public URLs ----
    public_app_url: str = "http://localhost:8000"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (read .env once per process)."""
    return Settings()


settings = get_settings()
