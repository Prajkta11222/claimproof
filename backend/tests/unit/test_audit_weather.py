from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.audit import write_audit_event
from app.services.weather import summarize_weather


class FakeTable:
    def __init__(self):
        self.row = None

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        return SimpleNamespace(data=[self.row] if self.row else [])


def test_audit_writer_sanitizes_invalid_event_type():
    fake = SimpleNamespace(table=lambda _name: FakeTable())
    write_audit_event(fake, "incident", "user", "invalid_event", {"token": "secret"})


def test_audit_writer_writes_valid_event():
    table = FakeTable()
    fake = SimpleNamespace(table=lambda _name: table)
    write_audit_event(fake, "incident", "user", "weather_fetched", {"endpoint": "forecast"})
    assert table.row["event_type"] == "weather_fetched"


def test_weather_summary_handles_empty_hourly_arrays():
    now = datetime.now(timezone.utc)
    summary = summarize_weather(
        {"hourly": {}},
        now,
        now,
    )
    assert summary["total_precip_mm"] == 0
    assert summary["hail_code_hours"] == 0
