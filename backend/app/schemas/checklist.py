"""Checklist response models for deterministic evidence completeness."""

from __future__ import annotations

from pydantic import BaseModel


class ChecklistAction(BaseModel):
    type: str


class ChecklistItem(BaseModel):
    code: str
    severity: str
    status: str
    label: str
    hint: str
    action: ChecklistAction | None = None


class ChecklistResponse(BaseModel):
    items: list[ChecklistItem]
    completeness: str
