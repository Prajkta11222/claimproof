"""Incident CRUD endpoints with authorization on every query (SPEC section 7)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.errors import NotFoundError, ValidationError
from app.core.security import get_current_user
from app.db import get_supabase
from app.schemas.common import DeadlineResponse
from app.schemas.incidents import (
    IncidentCreateRequest,
    IncidentListItem,
    IncidentResponse,
    IncidentUpdateRequest,
    IntimationBrief,
)
from app.services.audit import write_audit_event
from app.services.checklist import compute_checklist
from app.services.deadline import (
    build_deadline_response,
    check_event_time_valid,
    compute_deadline,
    is_intimation_timely,
    normalize_event_time,
)

router = APIRouter()


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
async def create_incident(
    body: IncidentCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new incident with deadline computation."""
    sb = get_supabase()
    user_id = user["user_id"]

    # Validate event time
    is_valid, error_msg = check_event_time_valid(body.event_occurred_at)
    if not is_valid:
        raise ValidationError(error_msg, [{"field": "event_occurred_at", "issue": error_msg}])

    # Normalize and compute deadline
    normalized = normalize_event_time(body.event_occurred_at, body.event_time_precision)
    deadline_at = compute_deadline(body.event_occurred_at, body.event_time_precision)

    row = {
        "user_id": user_id,
        "scheme": body.scheme,
        "incident_type": body.incident_type,
        "description": body.description,
        "event_occurred_at": normalized.isoformat(),
        "event_time_precision": body.event_time_precision,
        "deadline_hours": 72,  # V1/A2
        "reporting_deadline_at": deadline_at.isoformat(),
        "crop_name": body.crop_name,
        "crop_season": body.crop_season,
        "survey_number": body.survey_number,
        "area_affected_acres": float(body.area_affected_acres)
        if body.area_affected_acres
        else None,
        "policy_reference": body.policy_reference,
        "location_lat": body.location.lat,
        "location_lng": body.location.lng,
        "location_accuracy_m": body.location.accuracy_m,
        "village": body.village,
        "taluka": body.taluka,
        "district": body.district,
        "state": body.state,
    }

    result = sb.table("incidents").insert(row).execute()
    incident = result.data[0]

    # Write audit event
    write_audit_event(
        sb,
        incident["id"],
        user_id,
        "incident_created",
        {
            "incident_type": body.incident_type,
            "event_occurred_at": normalized.isoformat(),
            "deadline_at": deadline_at.isoformat(),
        },
    )

    return _build_incident_response(incident, sb=sb)


@router.get("/incidents", response_model=list[IncidentListItem])
async def list_incidents(user: dict = Depends(get_current_user)):
    """List current user's incidents, newest first, max 50."""
    sb = get_supabase()
    user_id = user["user_id"]

    result = (
        sb.table("incidents")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    items = []
    for row in result.data:
        deadline = build_deadline_response(row)
        items.append(
            IncidentListItem(
                id=str(row["id"]),
                status=row["status"],
                incident_type=row["incident_type"],
                crop_name=row["crop_name"],
                district=row["district"],
                state=row["state"],
                event_occurred_at=str(row["event_occurred_at"]),
                created_at=str(row["created_at"]),
                deadline=DeadlineResponse(**deadline),
            )
        )

    return items


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str, user: dict = Depends(get_current_user)):
    """Get incident detail with deadline, photo counts, and intimations."""
    sb = get_supabase()
    incident = _get_owned_incident(sb, incident_id, user["user_id"])

    return _build_incident_response(incident, sb=sb)


@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    body: IncidentUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """Update incident fields. Recomputes deadline if event time changes."""
    sb = get_supabase()
    user_id = user["user_id"]
    old_incident = _get_owned_incident(sb, incident_id, user_id)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise ValidationError("No fields to update.")

    # Handle location nested object
    if "location" in updates:
        loc = updates.pop("location")
        updates["location_lat"] = loc["lat"]
        updates["location_lng"] = loc["lng"]
        if loc.get("accuracy_m") is not None:
            updates["location_accuracy_m"] = loc["accuracy_m"]

    # If event time or precision changes, validate and recompute deadline
    if "event_occurred_at" in updates or "event_time_precision" in updates:
        new_event_time = updates.get("event_occurred_at", old_incident["event_occurred_at"])
        if isinstance(new_event_time, str):
            new_event_time = datetime.fromisoformat(new_event_time)
        new_precision = updates.get("event_time_precision", old_incident["event_time_precision"])

        is_valid, error_msg = check_event_time_valid(new_event_time)
        if not is_valid:
            raise ValidationError(error_msg, [{"field": "event_occurred_at", "issue": error_msg}])

        normalized = normalize_event_time(new_event_time, new_precision)
        deadline_at = compute_deadline(new_event_time, new_precision)
        updates["event_occurred_at"] = normalized.isoformat()
        updates["reporting_deadline_at"] = deadline_at.isoformat()

    result = (
        sb.table("incidents").update(updates).eq("id", incident_id).eq("user_id", user_id).execute()
    )

    if not result.data:
        raise NotFoundError()

    # Audit with old/new values
    audit_payload = {"changes": {}}
    for key in updates:
        old_val = old_incident.get(key)
        new_val = updates[key]
        if str(old_val) != str(new_val):
            audit_payload["changes"][key] = {"old": str(old_val), "new": str(new_val)}

    if audit_payload["changes"]:
        write_audit_event(sb, incident_id, user_id, "incident_updated", audit_payload)

    return _build_incident_response(result.data[0], sb=sb)


@router.delete("/incidents/{incident_id}", status_code=204)
async def delete_incident(
    incident_id: str,
    confirm: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    """Hard delete incident including storage. Requires ?confirm=true."""
    if not confirm:
        raise ValidationError("Delete requires ?confirm=true parameter.")

    sb = get_supabase()
    user_id = user["user_id"]
    # Delete storage prefix (best effort)
    try:
        storage_prefix = f"{user_id}/{incident_id}"
        bucket = sb.storage.from_("evidence")
        # List and delete all files under this prefix
        files = bucket.list(storage_prefix)
        if files:
            for folder in files:
                subfolder_path = f"{storage_prefix}/{folder['name']}"
                subfiles = bucket.list(subfolder_path)
                if subfiles:
                    paths = [f"{subfolder_path}/{f['name']}" for f in subfiles]
                    bucket.remove(paths)
    except Exception:
        pass  # Storage cleanup is best-effort

    # Delete incident (cascade deletes photos, intimations, weather, reports, audit)
    sb.table("incidents").delete().eq("id", incident_id).eq("user_id", user_id).execute()

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_owned_incident(sb, incident_id: str, user_id: str) -> dict:
    """Fetch incident owned by user, or raise 404 (no existence leak)."""
    result = (
        sb.table("incidents").select("*").eq("id", incident_id).eq("user_id", user_id).execute()
    )
    if not result.data:
        raise NotFoundError()
    return result.data[0]


def _build_incident_response(incident: dict, sb=None) -> IncidentResponse:
    """Build full incident response with deadline and optional intimations."""
    deadline = build_deadline_response(incident)

    intimations = []
    photo_counts = {"total": 0, "passed": 0, "warn": 0, "fail": 0}
    checklist_summary = {"critical_missing": 0, "warnings": 0, "ok": 0}
    if sb:
        try:
            intim_result = (
                sb.table("intimation_records")
                .select("*")
                .eq("incident_id", incident["id"])
                .order("intimated_at")
                .execute()
            )
            deadline_at_dt = datetime.fromisoformat(str(incident["reporting_deadline_at"]))
            for row in intim_result.data:
                intimated_dt = datetime.fromisoformat(str(row["intimated_at"]))
                intimations.append(
                    IntimationBrief(
                        id=str(row["id"]),
                        channel=row["channel"],
                        intimated_at=str(row["intimated_at"]),
                        reference_number=row.get("reference_number"),
                        within_deadline=is_intimation_timely(intimated_dt, deadline_at_dt),
                    )
                )
            photos = (
                sb.table("photos")
                .select(
                    "shot_type,qc_status,gps_basis,distance_from_plot_m,time_basis,effective_taken_at"
                )
                .eq("incident_id", incident["id"])
                .execute()
                .data
            )
            photo_counts["total"] = len(photos)
            photo_counts["passed"] = sum(row.get("qc_status") == "pass" for row in photos)
            photo_counts["warn"] = sum(row.get("qc_status") == "warn" for row in photos)
            photo_counts["fail"] = sum(row.get("qc_status") == "fail" for row in photos)
            weather_rows = (
                sb.table("weather_snapshots")
                .select("id")
                .eq("incident_id", incident["id"])
                .limit(1)
                .execute()
                .data
            )
            checklist_summary = compute_checklist(
                incident,
                photos,
                intim_result.data,
                weather=weather_rows[0] if weather_rows else None,
            )["summary"]
        except Exception:
            pass

    return IncidentResponse(
        id=str(incident["id"]),
        user_id=str(incident["user_id"]),
        scheme=incident["scheme"],
        status=incident["status"],
        incident_type=incident["incident_type"],
        description=incident.get("description"),
        event_occurred_at=str(incident["event_occurred_at"]),
        event_time_precision=incident["event_time_precision"],
        deadline_hours=incident["deadline_hours"],
        reporting_deadline_at=str(incident["reporting_deadline_at"]),
        crop_name=incident["crop_name"],
        crop_season=incident.get("crop_season"),
        survey_number=incident.get("survey_number"),
        area_affected_acres=float(incident["area_affected_acres"])
        if incident.get("area_affected_acres")
        else None,
        policy_reference=incident.get("policy_reference"),
        location_lat=float(incident["location_lat"]),
        location_lng=float(incident["location_lng"]),
        location_accuracy_m=float(incident["location_accuracy_m"])
        if incident.get("location_accuracy_m")
        else None,
        village=incident.get("village"),
        taluka=incident.get("taluka"),
        district=incident["district"],
        state=incident["state"],
        created_at=str(incident["created_at"]),
        updated_at=str(incident["updated_at"]),
        deadline=DeadlineResponse(**deadline),
        photo_counts=photo_counts,
        checklist_summary=checklist_summary,
        intimations=intimations,
    )
