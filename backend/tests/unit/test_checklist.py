from datetime import datetime, timezone

from app.services.checklist import compute_checklist


def _incident(**overrides):
    incident = {
        "event_occurred_at": "2026-11-20T10:00:00+00:00",
        "reporting_deadline_at": "2026-11-23T10:00:00+00:00",
        "survey_number": "123/2",
        "area_affected_acres": 1.5,
        "description": "Hail damaged the crop across the north field.",
        "policy_reference": "POL-1",
    }
    return {**incident, **overrides}


def _photo(shot_type, **overrides):
    photo = {
        "shot_type": shot_type,
        "qc_status": "pass",
        "gps_basis": "client",
        "distance_from_plot_m": 42,
        "time_basis": "client",
        "effective_taken_at": "2026-11-20T11:00:00+00:00",
    }
    return {**photo, **overrides}


def test_checklist_requires_intimation_and_photo_minimum():
    result = compute_checklist(
        _incident(),
        [_photo("wide"), _photo("close_up")],
        [],
        now=datetime(2026, 11, 21, tzinfo=timezone.utc),
    )

    statuses = {item["code"]: item["status"] for item in result["items"]}
    assert statuses["INTIMATION_RECORDED"] == "missing"
    assert statuses["PHOTO_MIN_COUNT"] == "missing"
    assert result["completeness"] == "incomplete"
    assert result["summary"]["critical_missing"] == 2


def test_checklist_is_complete_when_required_evidence_is_present():
    photos = [
        _photo("wide"),
        _photo("close_up"),
        _photo("other"),
        _photo("other"),
        _photo("document"),
    ]
    result = compute_checklist(
        _incident(),
        photos,
        [{"intimated_at": "2026-11-21T09:00:00+00:00", "reference_number": "ACK-1"}],
        now=datetime(2026, 11, 21, tzinfo=timezone.utc),
    )

    assert result["completeness"] == "complete"
    assert result["summary"]["critical_missing"] == 0
    assert all(
        item["status"] == "ok"
        for item in result["items"]
        if item["severity"] in {"critical", "required"}
    )


def test_checklist_marks_late_intimation_as_warning():
    result = compute_checklist(
        _incident(),
        [],
        [{"intimated_at": "2026-11-23T10:01:00+00:00"}],
        now=datetime(2026, 11, 23, tzinfo=timezone.utc),
    )

    item = next(item for item in result["items"] if item["code"] == "INTIMATION_ON_TIME")
    assert item["status"] == "warn"
    assert result["completeness"] == "incomplete"
