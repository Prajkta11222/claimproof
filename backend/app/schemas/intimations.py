"""Intimation schemas per SPEC section 7 and section 8.5."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

VALID_CHANNELS = frozenset(
    {
        "crop_insurance_app",
        "helpline_14447",
        "insurer",
        "bank",
        "agri_department",
        "csc",
        "other",
    }
)


class IntimationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str
    intimated_at: datetime
    reference_number: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        if v not in VALID_CHANNELS:
            raise ValueError(f"Channel must be one of: {', '.join(sorted(VALID_CHANNELS))}")
        return v

    @field_validator("reference_number")
    @classmethod
    def validate_reference(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) > 60:
                raise ValueError("Reference number must be at most 60 characters.")
            if len(v) == 0:
                return None
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) > 500:
                raise ValueError("Notes must be at most 500 characters.")
            if len(v) == 0:
                return None
        return v


class IntimationResponse(BaseModel):
    id: str
    incident_id: str
    channel: str
    intimated_at: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    recorded_at: str
    created_at: str
    within_deadline: bool = False
