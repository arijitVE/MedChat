# shared/config.py — Centralized configuration (env-based, cached singleton)
# API keys, DB URLs, model configs, thresholds.
# All settings loaded from environment variables / .env file.

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Uses pydantic-settings v2. Values are read from environment variables
    first, then from a .env file if present. The singleton is cached via
    get_settings() so the .env file is parsed only once.
    """

    # --- Google Cloud / LLM ---
    OPENAI_API_KEY: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # --- Database ---
    DATABASE_URL: str = "postgresql://hdmis_user:hdmis_pass@localhost:5432/hdmis_db"

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Confidence Thresholds ---
    OCR_CONFIDENCE_THRESHOLD: float = 0.85
    FIELD_CONFIDENCE_THRESHOLD: float = 0.85
    FUZZY_MATCH_THRESHOLD: int = 85

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings.

    The first call reads from environment / .env file. Subsequent calls
    return the same instance without re-parsing.
    """
    return Settings()
