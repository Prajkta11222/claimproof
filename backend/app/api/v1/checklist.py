"""Computed incident checklist endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.errors import NotFoundError
from app.core.security import get_current_user
from app.db import get_supabase
from app.schemas.checklist import ChecklistResponse
from app.services.checklist import compute_checklist

router = APIRouter()


@router.get("/incidents/{incident_id}/checklist", response_model=ChecklistResponse)
async def get_checklist(incident_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    user_id = user["user_id"]
    incident_result = (
        sb.table("incidents").select("*").eq("id", incident_id).eq("user_id", user_id).execute()
    )
    if not incident_result.data:
        raise NotFoundError()

    photos = (
        sb.table("photos")
        .select("shot_type,qc_status,gps_basis,distance_from_plot_m,time_basis,effective_taken_at")
        .eq("incident_id", incident_id)
        .execute()
    ).data
    intimations = (
        sb.table("intimation_records")
        .select("intimated_at,reference_number")
        .eq("incident_id", incident_id)
        .execute()
    ).data
    weather = (
        sb.table("weather_snapshots").select("id").eq("incident_id", incident_id).limit(1).execute()
    ).data
    return compute_checklist(
        incident_result.data[0],
        photos,
        intimations,
        weather=weather[0] if weather else None,
    )
