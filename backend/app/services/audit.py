"""Audit event writer — append-only chain of custody (SPEC section 6.2)."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

VALID_EVENT_TYPES = frozenset(
    {
        "incident_created",
        "incident_updated",
        "photo_uploaded",
        "photo_deleted",
        "intimation_recorded",
        "intimation_deleted",
        "weather_fetched",
        "report_generated",
        "report_downloaded",
    }
)


def write_audit_event(
    supabase_client: Any,
    incident_id: str | None,
    user_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Insert an audit event. Payload must never contain tokens or signed URLs."""
    if event_type not in VALID_EVENT_TYPES:
        logger.error("invalid_audit_event_type", event_type=event_type)
        return

    # Sanitize payload — never store tokens or signed URLs
    safe_payload = payload or {}

    try:
        supabase_client.table("audit_events").insert(
            {
                "incident_id": incident_id,
                "user_id": user_id,
                "event_type": event_type,
                "payload": safe_payload,
            }
        ).execute()
    except Exception:
        # Audit failures must not break the main flow
        logger.exception("audit_write_failed", event_type=event_type)
