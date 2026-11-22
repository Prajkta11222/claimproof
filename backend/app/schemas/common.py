"""Shared Pydantic models for API responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    field: str = ""
    issue: str = ""


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []
    request_id: str = ""


class ErrorResponse(BaseModel):
    error: ErrorBody


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float
    lng: float
    accuracy_m: Optional[float] = None


class DeadlineResponse(BaseModel):
    deadline_at: str
    server_time: str
    seconds_remaining: int
    state: str  # ACTIVE | URGENT | CRITICAL | EXPIRED
    rule: str
    assumptions: list[str] = []


class PhotoCountsResponse(BaseModel):
    total: int = 0
    passed: int = 0
    warn: int = 0
    fail: int = 0


class ChecklistSummaryResponse(BaseModel):
    critical_missing: int = 0
    warnings: int = 0
    ok: int = 0
