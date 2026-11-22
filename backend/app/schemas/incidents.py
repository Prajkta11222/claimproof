"""Incident schemas with validation per SPEC section 7.2."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import (
    ChecklistSummaryResponse,
    DeadlineResponse,
    LocationInput,
    PhotoCountsResponse,
)

VALID_INCIDENT_TYPES = frozenset(
    {
        "hailstorm",
        "inundation_flood",
        "landslide",
        "cloudburst",
        "natural_fire",
        "unseasonal_rain_post_harvest",
        "other",
    }
)

VALID_SEASONS = frozenset({"kharif", "rabi", "zaid", "other"})
VALID_SCHEMES = frozenset({"PMFBY", "OTHER"})


class IncidentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheme: str = "PMFBY"
    incident_type: str
    event_occurred_at: datetime
    event_time_precision: str
    description: Optional[str] = None
    crop_name: str
    crop_season: Optional[str] = None
    survey_number: Optional[str] = None
    area_affected_acres: Optional[float] = None
    policy_reference: Optional[str] = None
    location: LocationInput
    village: Optional[str] = None
    taluka: Optional[str] = None
    district: str
    state: str

    @field_validator("scheme")
    @classmethod
    def validate_scheme(cls, v: str) -> str:
        if v not in VALID_SCHEMES:
            raise ValueError(f"Scheme must be one of: {', '.join(sorted(VALID_SCHEMES))}")
        return v

    @field_validator("incident_type")
    @classmethod
    def validate_incident_type(cls, v: str) -> str:
        if v not in VALID_INCIDENT_TYPES:
            raise ValueError(f"Invalid incident type: {v}")
        return v

    @field_validator("event_time_precision")
    @classmethod
    def validate_precision(cls, v: str) -> str:
        if v not in ("exact", "date_only"):
            raise ValueError("Precision must be 'exact' or 'date_only'.")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) > 1000:
                raise ValueError("Description must be at most 1000 characters.")
            if len(v) == 0:
                return None
        return v

    @field_validator("crop_name")
    @classmethod
    def validate_crop_name(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 60:
            raise ValueError("Crop name must be between 1 and 60 characters.")
        return v

    @field_validator("crop_season")
    @classmethod
    def validate_season(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_SEASONS:
            raise ValueError(f"Season must be one of: {', '.join(sorted(VALID_SEASONS))}")
        return v

    @field_validator("survey_number")
    @classmethod
    def validate_survey_number(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) > 40:
                raise ValueError("Survey number must be at most 40 characters.")
            if len(v) == 0:
                return None
        return v

    @field_validator("area_affected_acres")
    @classmethod
    def validate_area(cls, v: float | None) -> float | None:
        if v is not None and (v <= 0 or v > 10000):
            raise ValueError("Affected area must be between 0 and 10,000 acres.")
        return v

    @field_validator("policy_reference")
    @classmethod
    def validate_policy_ref(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) > 40:
                raise ValueError("Policy reference must be at most 40 characters.")
            if len(v) == 0:
                return None
        return v

    @field_validator("district", "state")
    @classmethod
    def validate_required_text(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 80:
            raise ValueError("Field must be between 1 and 80 characters.")
        return v

    @field_validator("village", "taluka")
    @classmethod
    def validate_optional_text(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) > 80:
                raise ValueError("Field must be at most 80 characters.")
            if len(v) == 0:
                return None
        return v


class IncidentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = None
    incident_type: Optional[str] = None
    event_occurred_at: Optional[datetime] = None
    event_time_precision: Optional[str] = None
    description: Optional[str] = None
    crop_name: Optional[str] = None
    crop_season: Optional[str] = None
    survey_number: Optional[str] = None
    area_affected_acres: Optional[float] = None
    policy_reference: Optional[str] = None
    location: Optional[LocationInput] = None
    village: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("open", "archived"):
            raise ValueError("Status must be 'open' or 'archived'.")
        return v

    @field_validator("incident_type")
    @classmethod
    def validate_incident_type(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_INCIDENT_TYPES:
            raise ValueError(f"Invalid incident type: {v}")
        return v

    @field_validator("event_time_precision")
    @classmethod
    def validate_precision(cls, v: str | None) -> str | None:
        if v is not None and v not in ("exact", "date_only"):
            raise ValueError("Precision must be 'exact' or 'date_only'.")
        return v

    @field_validator("crop_name")
    @classmethod
    def validate_crop_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not 1 <= len(v) <= 60:
                raise ValueError("Crop name must be between 1 and 60 characters.")
        return v

    @field_validator("area_affected_acres")
    @classmethod
    def validate_area(cls, v: float | None) -> float | None:
        if v is not None and (v <= 0 or v > 10000):
            raise ValueError("Affected area must be between 0 and 10,000 acres.")
        return v


class IntimationBrief(BaseModel):
    id: str
    channel: str
    intimated_at: str
    reference_number: Optional[str] = None
    within_deadline: bool


class IncidentResponse(BaseModel):
    id: str
    user_id: str
    scheme: str
    status: str
    incident_type: str
    description: Optional[str] = None
    event_occurred_at: str
    event_time_precision: str
    deadline_hours: int
    reporting_deadline_at: str
    crop_name: str
    crop_season: Optional[str] = None
    survey_number: Optional[str] = None
    area_affected_acres: Optional[float] = None
    policy_reference: Optional[str] = None
    location_lat: float
    location_lng: float
    location_accuracy_m: Optional[float] = None
    village: Optional[str] = None
    taluka: Optional[str] = None
    district: str
    state: str
    created_at: str
    updated_at: str
    deadline: Optional[DeadlineResponse] = None
    photo_counts: PhotoCountsResponse = PhotoCountsResponse()
    checklist_summary: ChecklistSummaryResponse = ChecklistSummaryResponse()
    intimations: list[IntimationBrief] = []


class IncidentListItem(BaseModel):
    id: str
    status: str
    incident_type: str
    crop_name: str
    district: str
    state: str
    event_occurred_at: str
    created_at: str
    deadline: Optional[DeadlineResponse] = None
