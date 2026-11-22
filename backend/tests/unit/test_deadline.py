"""Deadline engine tests — full parametrized table from SPEC section 8.7."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.deadline import (
    build_deadline_response,
    check_event_time_valid,
    compute_deadline,
    get_deadline_state,
    is_intimation_timely,
    normalize_event_time,
)

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# Case 1: exact, simple
# event 2026-11-21 10:00 IST -> deadline 2026-11-24 10:00 IST
# ---------------------------------------------------------------------------
def test_exact_simple():
    event = datetime(2026, 11, 21, 10, 0, 0, tzinfo=IST)
    deadline = compute_deadline(event, "exact", 72)
    expected = datetime(2026, 11, 24, 10, 0, 0, tzinfo=IST).astimezone(timezone.utc)
    assert deadline == expected


# ---------------------------------------------------------------------------
# Case 2: date_only
# date 2026-11-21 -> event 2026-11-21 00:00 IST; deadline 2026-11-24 00:00 IST
# ---------------------------------------------------------------------------
def test_date_only():
    # For date_only, the input date is interpreted as IST midnight
    event = datetime(2026, 11, 21, 0, 0, 0, tzinfo=IST)
    deadline = compute_deadline(event, "date_only", 72)
    expected = datetime(2026, 11, 24, 0, 0, 0, tzinfo=IST).astimezone(timezone.utc)
    assert deadline == expected


def test_date_only_normalizes_to_midnight_ist():
    # Even if a time is provided with date_only, it normalizes to midnight IST
    event = datetime(2026, 11, 21, 15, 30, 0, tzinfo=IST)
    normalized = normalize_event_time(event, "date_only")
    expected = datetime(2026, 11, 21, 0, 0, 0, tzinfo=IST).astimezone(timezone.utc)
    assert normalized == expected


# ---------------------------------------------------------------------------
# Case 3: boundary 24h -> URGENT
# ---------------------------------------------------------------------------
def test_boundary_24h_urgent():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    deadline_at = now + timedelta(hours=24)
    state = get_deadline_state(deadline_at, now)
    assert state == "URGENT"


# ---------------------------------------------------------------------------
# Case 4: boundary 6h -> CRITICAL
# ---------------------------------------------------------------------------
def test_boundary_6h_critical():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    deadline_at = now + timedelta(hours=6)
    state = get_deadline_state(deadline_at, now)
    assert state == "CRITICAL"


# ---------------------------------------------------------------------------
# Case 5: boundary 0 -> EXPIRED
# ---------------------------------------------------------------------------
def test_boundary_0_expired():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    deadline_at = now  # exactly 0 remaining
    state = get_deadline_state(deadline_at, now)
    assert state == "EXPIRED"


# ---------------------------------------------------------------------------
# Case 6: future event (now + 6 min) -> validation error
# ---------------------------------------------------------------------------
def test_future_event_rejected():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    event = now + timedelta(minutes=6)
    is_valid, msg = check_event_time_valid(event, now)
    assert not is_valid
    assert "future" in msg.lower()


# ---------------------------------------------------------------------------
# Case 7: now + 4 min -> allowed (clock skew tolerance)
# ---------------------------------------------------------------------------
def test_near_future_allowed():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    event = now + timedelta(minutes=4)
    is_valid, msg = check_event_time_valid(event, now)
    assert is_valid
    assert msg is None


# ---------------------------------------------------------------------------
# Case 8: too old (now - 93 days) -> validation error
# ---------------------------------------------------------------------------
def test_too_old_rejected():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    event = now - timedelta(days=93)
    is_valid, msg = check_event_time_valid(event, now)
    assert not is_valid
    assert "older" in msg.lower() or "92" in msg


# ---------------------------------------------------------------------------
# Case 9: already late at creation (event now - 80h) -> state EXPIRED
# ---------------------------------------------------------------------------
def test_already_expired_at_creation():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    event = now - timedelta(hours=80)
    deadline = compute_deadline(event, "exact", 72)
    state = get_deadline_state(deadline, now)
    assert state == "EXPIRED"


# ---------------------------------------------------------------------------
# Case 10: UTC input — Z and +05:30 forms give same instant and same deadline
# ---------------------------------------------------------------------------
def test_utc_and_ist_give_same_deadline():
    # 2026-11-21T10:00:00+05:30 == 2026-11-21T04:30:00Z
    event_ist = datetime(2026, 11, 21, 10, 0, 0, tzinfo=IST)
    event_utc = datetime(2026, 11, 21, 4, 30, 0, tzinfo=timezone.utc)

    deadline_ist = compute_deadline(event_ist, "exact", 72)
    deadline_utc = compute_deadline(event_utc, "exact", 72)

    assert deadline_ist == deadline_utc


# ---------------------------------------------------------------------------
# Case 11: intimation timeliness check
# ---------------------------------------------------------------------------
def test_intimation_timely():
    deadline_at = datetime(2026, 11, 24, 10, 0, 0, tzinfo=timezone.utc)

    # Before deadline -> timely
    before = datetime(2026, 11, 23, 10, 0, 0, tzinfo=timezone.utc)
    assert is_intimation_timely(before, deadline_at) is True

    # Exactly at deadline -> timely
    at = deadline_at
    assert is_intimation_timely(at, deadline_at) is True

    # After deadline -> not timely
    after = datetime(2026, 11, 24, 10, 0, 1, tzinfo=timezone.utc)
    assert is_intimation_timely(after, deadline_at) is False


# ---------------------------------------------------------------------------
# Additional: deadline state transitions
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "hours_remaining,expected_state",
    [
        (48, "ACTIVE"),
        (25, "ACTIVE"),
        (24, "URGENT"),
        (23, "URGENT"),
        (12, "URGENT"),
        (6, "CRITICAL"),
        (5, "CRITICAL"),
        (1, "CRITICAL"),
        (0.001, "CRITICAL"),  # 3.6 seconds
        (0, "EXPIRED"),
        (-1, "EXPIRED"),
    ],
)
def test_deadline_state_parametrized(hours_remaining: float, expected_state: str):
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    deadline_at = now + timedelta(hours=hours_remaining)
    state = get_deadline_state(deadline_at, now)
    assert (
        state == expected_state
    ), f"hours_remaining={hours_remaining}: got {state}, expected {expected_state}"


# ---------------------------------------------------------------------------
# build_deadline_response
# ---------------------------------------------------------------------------
def test_build_deadline_response():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    incident = {
        "reporting_deadline_at": "2026-11-24T04:30:00+00:00",
    }
    resp = build_deadline_response(incident, now)
    assert resp["state"] == "ACTIVE"
    assert resp["seconds_remaining"] > 0
    assert resp["rule"] == "PMFBY_LOCALIZED_72H"
    assert "A1" in resp["assumptions"]
    assert "A2" in resp["assumptions"]
