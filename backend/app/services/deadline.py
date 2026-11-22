"""Deadline engine — pure functions, no I/O. Exhaustively unit-testable (SPEC section 8)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.rules import (
    CLOCK_SKEW_MINUTES,
    CRITICAL_THRESHOLD_H,
    DEADLINE_HOURS,
    EVENT_MAX_AGE_DAYS,
    URGENT_THRESHOLD_H,
)

IST = ZoneInfo("Asia/Kolkata")


def normalize_event_time(event_occurred_at: datetime, precision: str) -> datetime:
    """Normalize event time per section 8.2.

    - exact: convert to UTC as-is.
    - date_only: set to 00:00 IST that day (earliest possible, A1), then convert to UTC.
    """
    if precision == "date_only":
        # Extract the date in IST, set to midnight IST
        if event_occurred_at.tzinfo is None:
            event_occurred_at = event_occurred_at.replace(tzinfo=timezone.utc)
        ist_dt = event_occurred_at.astimezone(IST)
        midnight_ist = ist_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight_ist.astimezone(timezone.utc)
    else:
        # exact: ensure UTC
        if event_occurred_at.tzinfo is None:
            event_occurred_at = event_occurred_at.replace(tzinfo=timezone.utc)
        return event_occurred_at.astimezone(timezone.utc)


def compute_deadline(
    event_occurred_at: datetime,
    precision: str,
    deadline_hours: int = DEADLINE_HOURS,
) -> datetime:
    """Compute reporting deadline: event + deadline_hours (section 8.1)."""
    normalized = normalize_event_time(event_occurred_at, precision)
    return normalized + timedelta(hours=deadline_hours)


def get_deadline_state(deadline_at: datetime, now: datetime | None = None) -> str:
    """Determine deadline state per section 8.3.

    Boundary rules:
    - remaining == 24h -> URGENT
    - remaining == 6h  -> CRITICAL
    - remaining == 0   -> EXPIRED
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    remaining = deadline_at - now
    remaining_seconds = remaining.total_seconds()

    urgent_seconds = URGENT_THRESHOLD_H * 3600
    critical_seconds = CRITICAL_THRESHOLD_H * 3600

    if remaining_seconds <= 0:
        return "EXPIRED"
    elif remaining_seconds <= critical_seconds:
        return "CRITICAL"
    elif remaining_seconds <= urgent_seconds:
        return "URGENT"
    else:
        return "ACTIVE"


def build_deadline_response(incident_row: dict, now: datetime | None = None) -> dict:
    """Build the full deadline response object for an incident."""
    if now is None:
        now = datetime.now(timezone.utc)

    deadline_at = incident_row["reporting_deadline_at"]
    if isinstance(deadline_at, str):
        deadline_at = datetime.fromisoformat(deadline_at)
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)

    remaining = deadline_at - now
    seconds_remaining = max(0, int(remaining.total_seconds()))
    state = get_deadline_state(deadline_at, now)

    return {
        "deadline_at": deadline_at.isoformat().replace("+00:00", "Z"),
        "server_time": now.isoformat().replace("+00:00", "Z"),
        "seconds_remaining": seconds_remaining,
        "state": state,
        "rule": "PMFBY_LOCALIZED_72H",
        "assumptions": ["A1", "A2"],
    }


def check_event_time_valid(
    event_occurred_at: datetime, now: datetime | None = None
) -> tuple[bool, str | None]:
    """Validate event time per section 8.2.

    Returns (is_valid, error_message).
    - Not in the future (> 5 min tolerance for clock skew).
    - Not older than EVENT_MAX_AGE_DAYS.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if event_occurred_at.tzinfo is None:
        event_occurred_at = event_occurred_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    event_utc = event_occurred_at.astimezone(timezone.utc)

    # Not in the future beyond clock skew tolerance
    max_allowed = now + timedelta(minutes=CLOCK_SKEW_MINUTES)
    if event_utc > max_allowed:
        return False, "Event time cannot be in the future."

    # Not too old
    min_allowed = now - timedelta(days=EVENT_MAX_AGE_DAYS)
    if event_utc < min_allowed:
        return False, f"Event time cannot be older than {EVENT_MAX_AGE_DAYS} days."

    return True, None


def is_intimation_timely(intimated_at: datetime, deadline_at: datetime) -> bool:
    """Check if intimation was within the deadline (section 8.5)."""
    if intimated_at.tzinfo is None:
        intimated_at = intimated_at.replace(tzinfo=timezone.utc)
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)
    return intimated_at <= deadline_at
