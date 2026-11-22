from datetime import datetime, timedelta, timezone

from app.services.weather import summarize_weather


def test_summarize_weather_counts_precip_gust_and_hail_codes():
    start = datetime(2026, 11, 20, 4, 30, tzinfo=timezone.utc)
    end = start + timedelta(hours=24)
    raw = {
        "hourly": {
            "time": ["2026-11-20T10:00", "2026-11-20T11:00", "2026-11-20T12:00"],
            "precipitation": [2.0, 11.2, 5.0],
            "wind_gusts_10m": [30.0, 62.0, 40.0],
            "temperature_2m": [14.1, 22.0, 29.8],
            "weather_code": [61, 96, 99],
        },
    }

    summary = summarize_weather(raw, start, end)

    assert summary["total_precip_mm"] == 18.2
    assert summary["max_hourly_precip_mm"] == 11.2
    assert summary["max_gust_kmh"] == 62.0
    assert summary["temp_min_c"] == 14.1
    assert summary["temp_max_c"] == 29.8
    assert summary["hail_code_hours"] == 2
