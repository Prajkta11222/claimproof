"""Weather snapshot endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.errors import NotFoundError
from app.core.security import get_current_user
from app.db import get_supabase
from app.services.audit import write_audit_event
from app.services.weather import fetch_weather_snapshot

router = APIRouter()


def _owned_incident(sb, incident_id: str, user_id: str) -> dict:
    result = (
        sb.table("incidents").select("*").eq("id", incident_id).eq("user_id", user_id).execute()
    )
    if not result.data:
        raise NotFoundError()
    return result.data[0]


@router.post("/incidents/{incident_id}/weather/refresh")
async def refresh_weather(incident_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    incident = _owned_incident(sb, incident_id, user["user_id"])
    snapshot = await fetch_weather_snapshot(incident)
    if snapshot is None:
        return {"status": "unavailable", "snapshot": None}

    row = {
        "incident_id": incident_id,
        "source": "open-meteo",
        "endpoint": snapshot["endpoint"],
        "query_lat": snapshot["lat"],
        "query_lng": snapshot["lng"],
        "window_start": snapshot["window_start"],
        "window_end": snapshot["window_end"],
        "summary": snapshot["summary"],
        "raw": snapshot["raw"],
    }
    result = sb.table("weather_snapshots").insert(row).execute()
    write_audit_event(
        sb,
        incident_id,
        user["user_id"],
        "weather_fetched",
        {
            "endpoint": snapshot["endpoint"],
            "query_lat": snapshot["lat"],
            "query_lng": snapshot["lng"],
        },
    )
    return {"status": "available", "snapshot": result.data[0]}


@router.get("/incidents/{incident_id}/weather")
async def get_weather(incident_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    _owned_incident(sb, incident_id, user["user_id"])
    result = (
        sb.table("weather_snapshots")
        .select("*")
        .eq("incident_id", incident_id)
        .order("fetched_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else {"snapshot": None}
