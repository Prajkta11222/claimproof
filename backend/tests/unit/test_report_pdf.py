from app.services.report_pdf import generate_evidence_pdf, manifest_hash


def test_manifest_hash_is_sorted_and_deterministic():
    photos = [{"sha256": "bbbb"}, {"sha256": "aaaa"}]

    assert manifest_hash("incident-1", photos) == manifest_hash(
        "incident-1", list(reversed(photos))
    )


def test_generate_incomplete_evidence_pdf():
    incident = {
        "id": "12345678-abcd",
        "incident_type": "hailstorm",
        "description": "Hail damaged chickpea plants.",
        "event_occurred_at": "2026-11-20T10:00:00+00:00",
        "reporting_deadline_at": "2026-11-23T10:00:00+00:00",
        "location_lat": 21.1458,
        "location_lng": 79.0882,
        "district": "Nagpur",
        "state": "Maharashtra",
        "crop_name": "Chickpea",
        "scheme": "PMFBY",
    }
    checklist = {
        "completeness": "incomplete",
        "items": [
            {
                "label": "Official intimation",
                "severity": "critical",
                "status": "missing",
            }
        ],
    }

    pdf_bytes, sha256 = generate_evidence_pdf(
        incident,
        {"full_name": "Test Farmer"},
        [],
        [],
        None,
        checklist,
        1,
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
    assert len(sha256) == 64
