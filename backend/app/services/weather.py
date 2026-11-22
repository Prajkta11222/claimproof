"""Fail-soft Open-Meteo weather context (SPEC section 11)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import get_settings


def build_analysis_window(incident: dict[str, Any]) -> tuple[datetime, datetime]:
    event = _as_utc(incident["event_occurred_at"])
    now = datetime.now(timezone.utc)
    return event - timedelta(hours=12), min(now, event + timedelta(hours=72))


async def fetch_weather_snapshot(incident: dict[str, Any]) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.weather_enabled:
        return None

    lat = round(float(incident["location_lat"]), 2)
    lng = round(float(incident["location_lng"]), 2)
    start, end = build_analysis_window(incident)
    age_days = min(92, max(0, (datetime.now(timezone.utc) - start).days + 1))
    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": "temperature_2m,precipitation,rain,wind_speed_10m,wind_gusts_10m,weather_code",
        "past_days": age_days,
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
        "wind_speed_unit": "kmh",
    }

    async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
        for _ in range(2):
            try:
                response = await client.get(
                    f"{settings.open_meteo_base_url}/v1/forecast",
                    params=params,
                )
                response.raise_for_status()
                raw = response.json()
                return {
                    "summary": summarize_weather(raw, start, end),
                    "raw": raw,
                    "lat": lat,
                    "lng": lng,
                    "endpoint": "forecast",
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                }
            except Exception:
                continue

    return None


def summarize_weather(raw: dict[str, Any], start: datetime, end: datetime) -> dict[str, Any]:
    hourly = raw.get("hourly") or {}
    times = hourly.get("time") or []
    precip = hourly.get("precipitation") or []
    gust = hourly.get("wind_gusts_10m") or []
    temperature = hourly.get("temperature_2m") or []
    codes = hourly.get("weather_code") or []

    selected = []
    for index, time_value in enumerate(times):
        try:
            parsed = datetime.fromisoformat(str(time_value)).replace(
                tzinfo=timezone(timedelta(hours=5, minutes=30))
            )
            parsed = parsed.astimezone(timezone.utc)
        except Exception:
            continue
        if start <= parsed <= end:
            selected.append(index)

    def at(indices: list[int], values: list[Any]) -> list[float]:
        return [
            float(values[index])
            for index in indices
            if index < len(values) and values[index] is not None
        ]

    precip_values = at(selected, precip)
    gust_values = at(selected, gust)
    temp_values = at(selected, temperature)
    code_values = at(selected, codes)

    daily: list[dict[str, Any]] = []
    for time_value in dict.fromkeys(str(times[index]).split("T")[0] for index in selected):
        daily_indices = [index for index in selected if str(times[index]).startswith(time_value)]
        daily_precip = at(daily_indices, precip)
        daily_gust = at(daily_indices, gust)
        daily.append(
            {
                "date": time_value,
                "precip_mm": round(sum(daily_precip), 1),
                "max_gust_kmh": round(max(daily_gust), 1) if daily_gust else 0,
            }
        )

    return {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "total_precip_mm": round(sum(precip_values), 1),
        "max_hourly_precip_mm": round(max(precip_values), 1) if precip_values else 0,
        "max_gust_kmh": round(max(gust_values), 1) if gust_values else 0,
        "temp_min_c": round(min(temp_values), 1) if temp_values else None,
        "temp_max_c": round(max(temp_values), 1) if temp_values else None,
        "thunderstorm_hours": sum(code in (95, 96, 99) for code in code_values),
        "hail_code_hours": sum(code in (96, 99) for code in code_values),
        "daily": daily,
    }


def _as_utc(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
