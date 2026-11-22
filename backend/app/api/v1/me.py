"""Profile endpoints — GET /me, PATCH /me."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.errors import ValidationError
from app.core.security import get_current_user
from app.db import get_supabase
from app.schemas.profiles import ProfileResponse, ProfileUpdateRequest

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
async def get_or_create_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile. Creates one on first call (upsert)."""
    sb = get_supabase()
    user_id = user["user_id"]

    # Try to get existing profile
    result = sb.table("profiles").select("*").eq("id", user_id).execute()

    if result.data:
        row = result.data[0]
        return _row_to_response(row)

    # Create profile on first call
    new_profile = {
        "id": user_id,
        "full_name": "Farmer",
        "preferred_language": "en",
    }
    result = sb.table("profiles").insert(new_profile).execute()
    return _row_to_response(result.data[0])


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """Update profile fields (name, language, consent)."""
    sb = get_supabase()
    user_id = user["user_id"]

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise ValidationError("No fields to update.")

    # If consent_version is set, record consent_at
    if "consent_version" in updates:
        updates["consent_at"] = datetime.now(timezone.utc).isoformat()

    result = sb.table("profiles").update(updates).eq("id", user_id).execute()

    if not result.data:
        # Profile doesn't exist yet, create it
        new_profile = {"id": user_id, "full_name": "Farmer", "preferred_language": "en"}
        new_profile.update(updates)
        result = sb.table("profiles").insert(new_profile).execute()

    return _row_to_response(result.data[0])


def _row_to_response(row: dict) -> ProfileResponse:
    return ProfileResponse(
        id=str(row["id"]),
        full_name=row["full_name"],
        preferred_language=row["preferred_language"],
        consent_version=row.get("consent_version"),
        consent_at=row["consent_at"] if row.get("consent_at") else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
