"""Intimation record endpoints with validation per SPEC section 8.5."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.errors import NotFoundError, ValidationError
from app.core.rules import CLOCK_SKEW_MINUTES
from app.core.security import get_current_user
from app.db import get_supabase
from app.schemas.intimations import IntimationCreateRequest, IntimationResponse
from app.services.audit import write_audit_event
from app.services.deadline import is_intimation_timely

router = APIRouter()


@router.post(
    "/incidents/{incident_id}/intimations", response_model=IntimationResponse, status_code=201
)
async def create_intimation(
    incident_id: str,
    body: IntimationCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Record an intimation. Validates timing per section 8.5."""
    sb = get_supabase()
    user_id = user["user_id"]

    # Verify incident belongs to user
    incident = _get_owned_incident(sb, incident_id, user_id)

    now = datetime.now(timezone.utc)
    intimated_at = body.intimated_at
    if intimated_at.tzinfo is None:
        intimated_at = intimated_at.replace(tzinfo=timezone.utc)
    intimated_at_utc = intimated_at.astimezone(timezone.utc)

    # Validation: intimated_at > recorded_at + 5 min -> reject
    if intimated_at_utc > now + timedelta(minutes=CLOCK_SKEW_MINUTES):
        raise ValidationError(
            "Intimation time cannot be in the future.",
            [{"field": "intimated_at", "issue": "in the future"}],
        )

    # Validation: intimated_at < event_occurred_at -> reject
    event_time = datetime.fromisoformat(str(incident["event_occurred_at"]))
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    if intimated_at_utc < event_time:
        raise ValidationError(
            "Intimation time cannot be before the incident occurred.",
            [{"field": "intimated_at", "issue": "before event time"}],
        )

    # Insert
    row = {
        "incident_id": incident_id,
        "user_id": user_id,
        "channel": body.channel,
        "intimated_at": intimated_at_utc.isoformat(),
        "reference_number": body.reference_number,
        "notes": body.notes,
    }
    result = sb.table("intimation_records").insert(row).execute()
    record = result.data[0]

    # Audit
    write_audit_event(
        sb,
        incident_id,
        user_id,
        "intimation_recorded",
        {
            "intimation_id": record["id"],
            "channel": body.channel,
        },
    )

    deadline_at = datetime.fromisoformat(str(incident["reporting_deadline_at"]))
    return _row_to_response(record, deadline_at)


@router.get("/incidents/{incident_id}/intimations", response_model=list[IntimationResponse])
async def list_intimations(
    incident_id: str,
    user: dict = Depends(get_current_user),
):
    """List intimation records for an incident."""
    sb = get_supabase()
    user_id = user["user_id"]

    # Verify incident belongs to user
    incident = _get_owned_incident(sb, incident_id, user_id)

    result = (
        sb.table("intimation_records")
        .select("*")
        .eq("incident_id", incident_id)
        .order("intimated_at")
        .execute()
    )

    deadline_at = datetime.fromisoformat(str(incident["reporting_deadline_at"]))
    return [_row_to_response(row, deadline_at) for row in result.data]


@router.delete("/intimations/{intimation_id}", status_code=204)
async def delete_intimation(
    intimation_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete an intimation record. Verifies ownership through incident."""
    sb = get_supabase()
    user_id = user["user_id"]

    # Get the intimation and verify ownership
    result = (
        sb.table("intimation_records")
        .select("*")
        .eq("id", intimation_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise NotFoundError()

    record = result.data[0]

    # Audit before delete
    write_audit_event(
        sb,
        record["incident_id"],
        user_id,
        "intimation_deleted",
        {
            "intimation_id": intimation_id,
            "channel": record["channel"],
        },
    )

    sb.table("intimation_records").delete().eq("id", intimation_id).eq("user_id", user_id).execute()
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_owned_incident(sb, incident_id: str, user_id: str) -> dict:
    """Fetch incident owned by user, or raise 404."""
    result = (
        sb.table("incidents").select("*").eq("id", incident_id).eq("user_id", user_id).execute()
    )
    if not result.data:
        raise NotFoundError()
    return result.data[0]


def _row_to_response(row: dict, deadline_at: datetime) -> IntimationResponse:
    intimated_dt = datetime.fromisoformat(str(row["intimated_at"]))
    if intimated_dt.tzinfo is None:
        intimated_dt = intimated_dt.replace(tzinfo=timezone.utc)
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)

    return IntimationResponse(
        id=str(row["id"]),
        incident_id=str(row["incident_id"]),
        channel=row["channel"],
        intimated_at=str(row["intimated_at"]),
        reference_number=row.get("reference_number"),
        notes=row.get("notes"),
        recorded_at=str(row["recorded_at"]),
        created_at=str(row["created_at"]),
        within_deadline=is_intimation_timely(intimated_dt, deadline_at),
    )
