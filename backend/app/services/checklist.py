"""Deterministic missing-information checklist (SPEC section 12)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.rules import MIN_CLOSEUP_PHOTOS, MIN_PHOTOS, MIN_WIDE_PHOTOS


def _item(
    code: str,
    severity: str,
    status: str,
    label: str,
    hint: str,
    action_type: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "status": status,
        "label": label,
        "hint": hint,
    }
    if action_type:
        result["action"] = {"type": action_type}
    return result


def compute_checklist(
    incident: dict[str, Any],
    photos: list[dict[str, Any]],
    intimations: list[dict[str, Any]],
    now: datetime | None = None,
    weather: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute checklist items from current database state without persisting them."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    deadline = _as_utc(incident["reporting_deadline_at"])
    event_time = _as_utc(incident["event_occurred_at"])
    usable = [photo for photo in photos if photo.get("qc_status") in ("pass", "warn")]
    non_documents = [photo for photo in usable if photo.get("shot_type") != "document"]
    all_non_documents = [photo for photo in photos if photo.get("shot_type") != "document"]
    failed_non_documents = [
        photo
        for photo in photos
        if photo.get("shot_type") != "document" and photo.get("qc_status") == "fail"
    ]
    earliest_intimation = min(
        intimations,
        key=lambda row: _as_utc(row["intimated_at"]),
        default=None,
    )

    items = [
        _item(
            "INTIMATION_RECORDED",
            "critical",
            "ok" if intimations else "missing",
            "Official intimation recorded",
            "Inform an official channel now, then record it here.",
            "open_intimation_form",
        ),
        _item(
            "INTIMATION_ON_TIME",
            "critical",
            "missing"
            if not earliest_intimation
            else ("ok" if _as_utc(earliest_intimation["intimated_at"]) <= deadline else "warn"),
            "Intimation recorded within deadline",
            "Keep the reference number and contact your insurer if recorded late.",
        ),
        _item(
            "INTIMATION_REFERENCE",
            "recommended",
            "ok"
            if earliest_intimation and earliest_intimation.get("reference_number")
            else "missing",
            "Intimation reference number",
            "Add the ticket or SMS reference if you have one.",
        ),
        _item(
            "PHOTO_MIN_COUNT",
            "required",
            "ok" if len(non_documents) >= MIN_PHOTOS else "missing",
            "Minimum clear field photos",
            f"Add {max(0, MIN_PHOTOS - len(non_documents))} more clear photos.",
        ),
        _item(
            "PHOTO_WIDE",
            "required",
            "ok"
            if sum(photo.get("shot_type") == "wide" for photo in usable) >= MIN_WIDE_PHOTOS
            else "missing",
            "Wide field photo",
            "Add a wide photo showing the field boundary.",
        ),
        _item(
            "PHOTO_CLOSEUP",
            "required",
            "ok"
            if sum(photo.get("shot_type") == "close_up" for photo in usable) >= MIN_CLOSEUP_PHOTOS
            else "missing",
            "Close-up of damage",
            "Add a close-up of damaged plants.",
        ),
        _item(
            "PHOTO_QUALITY",
            "required",
            "ok"
            if not all_non_documents or len(failed_non_documents) < len(all_non_documents) / 2
            else "missing",
            "Photo quality",
            "Retake blurry or dark photos.",
        ),
        _item(
            "PHOTO_LOCATION",
            "required",
            "ok"
            if any(
                photo.get("gps_basis")
                and photo.get("distance_from_plot_m") is not None
                and photo["distance_from_plot_m"] <= 500
                for photo in usable
            )
            else "missing",
            "Photo location",
            "Take at least one photo at the plot with location enabled.",
        ),
        _item(
            "PHOTO_TIME",
            "required",
            "ok"
            if any(
                photo.get("time_basis") != "upload"
                and event_time - timedelta(hours=1) <= _as_utc(photo["effective_taken_at"]) <= now
                for photo in usable
            )
            else "missing",
            "Photo capture time",
            "Use the in-app camera so a capture time is available.",
        ),
        _item(
            "SURVEY_NUMBER",
            "required",
            "ok" if incident.get("survey_number") else "missing",
            "Survey or gat number",
            "Add your survey or gat number.",
        ),
        _item(
            "AREA_AFFECTED",
            "required",
            "ok" if incident.get("area_affected_acres", 0) > 0 else "missing",
            "Affected area",
            "Add the affected area in acres.",
        ),
        _item(
            "POLICY_REFERENCE",
            "recommended",
            "ok" if incident.get("policy_reference") else "missing",
            "Policy or enrollment reference",
            "Add your enrollment or policy number.",
        ),
        _item(
            "DESCRIPTION",
            "recommended",
            "ok" if len((incident.get("description") or "").strip()) >= 20 else "missing",
            "Incident description",
            "Describe what happened in at least 20 characters.",
        ),
        _item(
            "WEATHER_CONTEXT",
            "recommended",
            "ok" if weather else "missing",
            "Weather context",
            "Weather could not be loaded. Tap refresh.",
        ),
        _item(
            "INTIMATION_PROOF_DOC",
            "recommended",
            "ok" if any(photo.get("shot_type") == "document" for photo in photos) else "missing",
            "Intimation proof",
            "Add a screenshot of the acknowledgement SMS or app screen.",
        ),
    ]

    blocking = {"critical", "required"}
    completeness = (
        "complete"
        if not any(
            item["severity"] in blocking and item["status"] in {"missing", "warn"} for item in items
        )
        else "incomplete"
    )
    summary = {
        "critical_missing": sum(
            item["severity"] == "critical" and item["status"] in {"missing", "warn"}
            for item in items
        ),
        "warnings": sum(item["status"] == "warn" for item in items),
        "ok": sum(item["status"] == "ok" for item in items),
    }
    return {"items": items, "completeness": completeness, "summary": summary}


def _as_utc(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
