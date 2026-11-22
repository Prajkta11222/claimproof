"""Photo schemas per SPEC §7.1 and §7.2."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class QcCheck(BaseModel):
    code: str
    status: str  # pass | warn | fail
    value: Any = None
    message: str


class PhotoUrls(BaseModel):
    thumb: str = ""
    display: str = ""
    expires_at: Optional[str] = None


class PhotoResponse(BaseModel):
    id: str
    incident_id: str
    user_id: str
    sha256: str
    source: str
    shot_type: str
    width_px: int
    height_px: int
    size_bytes: int
    mime_type: str
    has_exif: bool
    effective_taken_at: str
    time_basis: str
    gps_basis: Optional[str] = None
    distance_from_plot_m: Optional[float] = None
    qc_status: str  # pending | pass | warn | fail
    qc_checks: list[QcCheck] = []
    ai_status: str = "pending"
    ai_attempts: int = 0
    ai_result: Optional[dict[str, Any]] = None
    uploaded_at: str
    created_at: str
    urls: PhotoUrls = PhotoUrls()


class PhotoPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_type: str

    @field_validator("shot_type")
    @classmethod
    def validate_shot_type(cls, v: str) -> str:
        if v not in ("wide", "close_up", "document", "other"):
            raise ValueError("Shot type must be one of: wide, close_up, document, other.")
        return v
