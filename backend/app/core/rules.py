"""Threshold constants and business rules. All tunable values live here (SPEC section 5.5)."""

import os


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


# ---------------------------------------------------------------------------
# Deadline
# ---------------------------------------------------------------------------
DEADLINE_HOURS = _env_int("DEADLINE_HOURS_DEFAULT", 72)
URGENT_THRESHOLD_H = 24  # UX choice
CRITICAL_THRESHOLD_H = 6  # UX choice

# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------
MAX_UPLOAD_BYTES = _env_int("MAX_UPLOAD_MB", 12) * 1024 * 1024
MAX_PHOTOS_PER_INCIDENT = _env_int("MAX_PHOTOS_PER_INCIDENT", 12)
MAX_IMAGE_PIXELS = _env_int("MAX_IMAGE_PIXELS", 50_000_000)

# ---------------------------------------------------------------------------
# Photo requirements — A3: TODO: calibrate; ask insurer/surveyor for official count
# ---------------------------------------------------------------------------
MIN_PHOTOS = 4  # A3
RECOMMENDED_PHOTOS = 8  # A3
MIN_WIDE_PHOTOS = 1  # A3
MIN_CLOSEUP_PHOTOS = 1  # A3

# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------
DISPLAY_LONG_EDGE = 1600  # px
THUMB_LONG_EDGE = 320  # px
AI_LONG_EDGE = 1024  # px

# ---------------------------------------------------------------------------
# GPS thresholds — A5: TODO: tune after field tests
# ---------------------------------------------------------------------------
GPS_WARN_M = 500  # A5 — >500m = warn
GPS_STRONG_WARN_M = 2000  # A5 — >2km = strong warn (never auto-fail)

# ---------------------------------------------------------------------------
# Event age
# ---------------------------------------------------------------------------
EVENT_MAX_AGE_DAYS = _env_int("EVENT_MAX_AGE_DAYS", 92)

# ---------------------------------------------------------------------------
# Clock skew tolerance
# ---------------------------------------------------------------------------
CLOCK_SKEW_MINUTES = 5

# ---------------------------------------------------------------------------
# QC thresholds — A4: TODO: calibrate on >=30 real phone photos on build day 2
# ---------------------------------------------------------------------------
BLUR_PASS = 100  # variance of Laplacian
BLUR_WARN = 30
EXPOSURE_PASS_LOW = 50  # mean luminance 0-255
EXPOSURE_PASS_HIGH = 210
EXPOSURE_WARN_LOW = 35
EXPOSURE_WARN_HIGH = 225
RESOLUTION_PASS = 1280  # long edge px
RESOLUTION_WARN = 640

# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------
AI_MAX_ATTEMPTS_PER_PHOTO = 3
AI_TIMEOUT_SECONDS = 20  # A9

# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
REPORT_MAX_PER_INCIDENT_PER_HOUR = _env_int("REPORT_MAX_PER_INCIDENT_PER_HOUR", 10)

# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------
RATE_LIMIT_DEFAULT = _env_str("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_UPLOAD = _env_str("RATE_LIMIT_UPLOAD", "20/minute")

# ---------------------------------------------------------------------------
# Upload concurrency (semaphore, caps RAM on 512 MB instance)
# ---------------------------------------------------------------------------
UPLOAD_CONCURRENCY = _env_int("UPLOAD_CONCURRENCY", 2)

# ---------------------------------------------------------------------------
# Signed URL TTL
# ---------------------------------------------------------------------------
SIGNED_URL_TTL_SECONDS = _env_int("SIGNED_URL_TTL_SECONDS", 600)

# ---------------------------------------------------------------------------
# Weather — V8/A10
# ---------------------------------------------------------------------------
WEATHER_TIMEOUT_SECONDS = 8
WEATHER_CACHE_MAX_AGE_SECONDS = 3600  # 1 hour
