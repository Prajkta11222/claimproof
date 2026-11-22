"""Application configuration via pydantic-settings. Fails fast on missing required vars."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_allowed_origins: str = "http://localhost:5173"

    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_storage_bucket: str = "evidence"
    signed_url_ttl_seconds: int = 600

    # JWT (A8) — TODO: check project dashboard on day 1 for JWKS vs HS256
    supabase_jwks_url: Optional[str] = None
    supabase_jwt_secret: Optional[str] = None
    supabase_jwt_issuer: str = ""
    supabase_jwt_audience: str = "authenticated"

    # Gemini — A9: TODO: verify current terms before using real farmer data
    ai_enabled: bool = True
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    ai_timeout_seconds: int = 20
    ai_max_attempts_per_photo: int = 3

    # Weather — V8/A10: TODO: subscription or self-host needed for production/commercial use
    weather_enabled: bool = True
    open_meteo_base_url: str = "https://api.open-meteo.com"
    open_meteo_archive_url: str = "https://archive-api.open-meteo.com"
    weather_timeout_seconds: int = 8

    # Limits
    deadline_hours_default: int = 72
    event_max_age_days: int = 92
    max_upload_mb: int = 12
    max_photos_per_incident: int = 12
    max_image_pixels: int = 50_000_000
    upload_concurrency: int = 2
    report_max_per_incident_per_hour: int = 10
    rate_limit_default: str = "60/minute"
    rate_limit_upload: str = "20/minute"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @model_validator(mode="after")
    def validate_jwt_config(self) -> Settings:
        if not self.supabase_jwks_url and not self.supabase_jwt_secret:
            raise ValueError("Either SUPABASE_JWKS_URL or SUPABASE_JWT_SECRET must be set (A8)")
        return self

    @model_validator(mode="after")
    def validate_ai_config(self) -> Settings:
        if self.ai_enabled and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_ENABLED=true")
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Fails fast on missing required vars."""
    return Settings()
