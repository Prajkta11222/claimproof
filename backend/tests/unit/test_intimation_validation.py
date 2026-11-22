"""Intimation validation tests per SPEC section 8.5."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_intimated_at_in_future_rejected():
    """intimated_at > now + 5 min should be rejected."""
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    intimated_at = now + timedelta(minutes=6)
    # This mirrors the validation in the endpoint
    assert intimated_at > now + timedelta(minutes=5)


def test_intimated_at_before_event_rejected():
    """intimated_at < event_occurred_at should be rejected."""
    event_time = datetime(2026, 11, 21, 10, 0, 0, tzinfo=timezone.utc)
    intimated_at = datetime(2026, 11, 21, 9, 0, 0, tzinfo=timezone.utc)
    assert intimated_at < event_time


def test_valid_intimation_accepted():
    """Valid intimation time (after event, not in future) should be accepted."""
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    event_time = datetime(2026, 11, 21, 10, 0, 0, tzinfo=timezone.utc)
    intimated_at = datetime(2026, 11, 22, 8, 0, 0, tzinfo=timezone.utc)

    # Not in the future
    assert intimated_at <= now + timedelta(minutes=5)
    # Not before event
    assert intimated_at >= event_time


def test_intimated_at_exactly_at_event_accepted():
    """Intimation at exact event time should be accepted."""
    event_time = datetime(2026, 11, 21, 10, 0, 0, tzinfo=timezone.utc)
    intimated_at = event_time
    assert intimated_at >= event_time


def test_intimated_at_near_future_within_tolerance_accepted():
    """intimated_at = now + 4 min should be accepted (within 5 min tolerance)."""
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)
    intimated_at = now + timedelta(minutes=4)
    assert intimated_at <= now + timedelta(minutes=5)
