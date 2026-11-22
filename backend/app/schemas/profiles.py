"""Profile schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ProfileResponse(BaseModel):
    id: str
    full_name: str
    preferred_language: str
    consent_version: Optional[str] = None
    consent_at: Optional[str] = None
    created_at: str
    updated_at: str


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = None
    preferred_language: Optional[str] = None
    consent_version: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not 1 <= len(v) <= 100:
                raise ValueError("Full name must be between 1 and 100 characters.")
        return v

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v not in ("en", "mr", "hi"):
            raise ValueError("Language must be one of: en, mr, hi.")
        return v
