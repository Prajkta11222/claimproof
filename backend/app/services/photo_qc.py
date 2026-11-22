"""Deterministic Photo QC service (SPEC §9.2, §9.3, §9.4)."""

from __future__ import annotations

import hashlib
import io
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Tuple

import numpy as np
from PIL import Image, ImageOps

from app.core.rules import (
    BLUR_PASS,
    BLUR_WARN,
    DISPLAY_LONG_EDGE,
    EXPOSURE_PASS_HIGH,
    EXPOSURE_PASS_LOW,
    EXPOSURE_WARN_HIGH,
    EXPOSURE_WARN_LOW,
    GPS_STRONG_WARN_M,
    GPS_WARN_M,
    MAX_IMAGE_PIXELS,
    RESOLUTION_PASS,
    RESOLUTION_WARN,
    THUMB_LONG_EDGE,
)

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 1)


def compute_sha256(data: bytes) -> str:
    """Compute exact SHA-256 hash of byte array (SPEC §9.2 step 3)."""
    return hashlib.sha256(data).hexdigest()


def calculate_blur_laplacian(img_gray: Image.Image) -> float:
    """Compute variance of the Laplacian using numpy on a grayscale image."""
    arr = np.asarray(img_gray, dtype=np.float64)
    # 3x3 Laplacian kernel
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)

    # Manual convolution via slicing for zero additional dependencies
    padded = np.pad(arr, pad_width=1, mode="edge")
    conv = (
        kernel[0, 1] * padded[:-2, 1:-1]
        + kernel[1, 0] * padded[1:-1, :-2]
        + kernel[1, 1] * padded[1:-1, 1:-1]
        + kernel[1, 2] * padded[1:-1, 2:]
        + kernel[2, 1] * padded[2:, 1:-1]
    )
    variance = float(np.var(conv))
    return round(variance, 2)


def calculate_luminance(img_gray: Image.Image) -> float:
    """Calculate mean luminance (0-255)."""
    arr = np.asarray(img_gray, dtype=np.float64)
    return round(float(np.mean(arr)), 1)


def process_and_qc_image(
    image_bytes: bytes,
    source: str,
    shot_type: str,
    incident: dict[str, Any],
    exif_data: dict[str, Any],
    client_reported_at: datetime | None,
    client_gps_lat: float | None,
    client_gps_lng: float | None,
    is_reused_in_other_incident: bool = False,
    now: datetime | None = None,
) -> Tuple[dict[str, Any], bytes, bytes]:
    """Run full deterministic QC pipeline and generate display and thumb images.

    Returns:
      (photo_metadata_dict, display_bytes, thumb_bytes)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. Verify decode with Pillow (SPEC §9.2 Step 5)
    bio = io.BytesIO(image_bytes)
    with Image.open(bio) as img:
        img.verify()

    # Reopen after verify
    bio.seek(0)
    img = Image.open(bio)
    format_name = (img.format or "").upper()
    if format_name not in ("JPEG", "JPG", "PNG", "WEBP"):
        raise ValueError(f"Unsupported format {format_name}. Must be JPEG, PNG, or WebP.")

    # Apply EXIF orientation
    img = ImageOps.exif_transpose(img)
    width, height = img.size
    long_edge = max(width, height)

    # 2. Derive display.jpg (1600px long edge, q85, EXIF stripped) and thumb.jpg (320px)
    display_img = img.copy()
    if long_edge > DISPLAY_LONG_EDGE:
        display_img.thumbnail((DISPLAY_LONG_EDGE, DISPLAY_LONG_EDGE), Image.Resampling.LANCZOS)
    display_buf = io.BytesIO()
    display_img.convert("RGB").save(display_buf, format="JPEG", quality=85)
    display_bytes = display_buf.getvalue()

    thumb_img = img.copy()
    thumb_img.thumbnail((THUMB_LONG_EDGE, THUMB_LONG_EDGE), Image.Resampling.LANCZOS)
    thumb_buf = io.BytesIO()
    thumb_img.convert("RGB").save(thumb_buf, format="JPEG", quality=80)
    thumb_bytes = thumb_buf.getvalue()

    # 3. Time Resolution (SPEC §9.4)
    # Priority: EXIF DateTimeOriginal -> client_reported_at (camera only) -> uploaded_at (now)
    time_basis = "upload"
    effective_taken_at = now
    if exif_data.get("taken_at"):
        effective_taken_at = exif_data["taken_at"]
        time_basis = "exif"
    elif source == "camera_capture" and client_reported_at:
        effective_taken_at = client_reported_at
        time_basis = "client"

    # 4. GPS Resolution (SPEC §9.4)
    # Priority: EXIF GPS -> client GPS (camera only)
    gps_basis = None
    photo_lat = None
    photo_lng = None
    if exif_data.get("gps_lat") is not None and exif_data.get("gps_lng") is not None:
        photo_lat = exif_data["gps_lat"]
        photo_lng = exif_data["gps_lng"]
        gps_basis = "exif"
    elif source == "camera_capture" and client_gps_lat is not None and client_gps_lng is not None:
        photo_lat = client_gps_lat
        photo_lng = client_gps_lng
        gps_basis = "client"

    # Distance calculation if GPS present
    plot_lat = float(incident["location_lat"])
    plot_lng = float(incident["location_lng"])
    distance_m = None
    if photo_lat is not None and photo_lng is not None:
        distance_m = haversine_distance_m(photo_lat, photo_lng, plot_lat, plot_lng)

    # 5. Deterministic Checks on a <= 1024 px grayscale copy (SPEC §9.3)
    analysis_img = img.copy().convert("L")
    if long_edge > 1024:
        analysis_img.thumbnail((1024, 1024), Image.Resampling.BILINEAR)

    blur_val = calculate_blur_laplacian(analysis_img)
    exposure_val = calculate_luminance(analysis_img)

    qc_checks: list[dict[str, Any]] = []

    # FILE_OK
    qc_checks.append(
        {
            "code": "FILE_OK",
            "status": "pass",
            "value": len(image_bytes),
            "message": "File read and decoded successfully.",
        }
    )

    # RESOLUTION
    if long_edge >= RESOLUTION_PASS:
        res_status = "pass"
        res_msg = f"Resolution is clear ({width}x{height})."
    elif long_edge >= RESOLUTION_WARN:
        res_status = "warn"
        res_msg = "Photo is moderate size. Retake with original camera for best results."
    else:
        res_status = "fail"
        res_msg = "Photo is too small. Retake with the normal camera, not a chat app copy."

    # Documents skip blur/exposure fail (they only warn, SPEC §9.5)
    is_doc = shot_type == "document"

    # BLUR
    if blur_val >= BLUR_PASS:
        blur_status = "pass"
        blur_msg = "Sharp enough."
    elif blur_val >= BLUR_WARN:
        blur_status = "warn"
        blur_msg = "Photo looks slightly blurry. Hold steady and tap screen to focus."
    else:
        blur_status = "warn" if is_doc else "fail"
        blur_msg = "Photo looks blurry. Hold steady, tap the screen to focus, and retake."

    qc_checks.append(
        {"code": "RESOLUTION", "status": res_status, "value": long_edge, "message": res_msg}
    )
    qc_checks.append(
        {"code": "BLUR", "status": blur_status, "value": blur_val, "message": blur_msg}
    )

    # EXPOSURE
    if EXPOSURE_PASS_LOW <= exposure_val <= EXPOSURE_PASS_HIGH:
        exp_status = "pass"
        exp_msg = "Good lighting and exposure."
    elif (EXPOSURE_WARN_LOW <= exposure_val < EXPOSURE_PASS_LOW) or (
        EXPOSURE_PASS_HIGH < exposure_val <= EXPOSURE_WARN_HIGH
    ):
        exp_status = "warn"
        exp_msg = "Lighting could be better. Adjust angle so light is not behind crop."
    else:
        exp_status = "warn" if is_doc else "fail"
        exp_msg = "Too dark or too bright. Move so light is illuminating the crop."

    qc_checks.append(
        {"code": "EXPOSURE", "status": exp_status, "value": exposure_val, "message": exp_msg}
    )

    # EXIF_PRESENT
    if exif_data.get("has_exif"):
        qc_checks.append(
            {
                "code": "EXIF_PRESENT",
                "status": "pass",
                "value": True,
                "message": "Camera metadata preserved.",
            }
        )
    else:
        qc_checks.append(
            {
                "code": "EXIF_PRESENT",
                "status": "warn",
                "value": False,
                "message": "No camera details found. This is common for WhatsApp/screenshots.",
            }
        )

    # TIME CHECKS
    event_time = datetime.fromisoformat(str(incident["event_occurred_at"]))
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)

    # TIME_BEFORE_EVENT
    if effective_taken_at < event_time - timedelta(hours=1):
        qc_checks.append(
            {
                "code": "TIME_BEFORE_EVENT",
                "status": "warn",
                "value": effective_taken_at.isoformat(),
                "message": "Photo time is earlier than the declared incident time.",
            }
        )

    # TIME_CLOCK_AHEAD
    if effective_taken_at > now + timedelta(minutes=5):
        qc_checks.append(
            {
                "code": "TIME_CLOCK_AHEAD",
                "status": "warn",
                "value": effective_taken_at.isoformat(),
                "message": "Photo timestamp is in the future. Check your device clock.",
            }
        )

    # OLD_PHOTO
    if now - effective_taken_at > timedelta(hours=24):
        qc_checks.append(
            {
                "code": "OLD_PHOTO",
                "status": "warn",
                "value": round((now - effective_taken_at).total_seconds() / 3600, 1),
                "message": "Photo was taken more than 24 hours before upload.",
            }
        )

    # LATE_PHOTO
    deadline_at = datetime.fromisoformat(str(incident["reporting_deadline_at"]))
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)
    if effective_taken_at > deadline_at:
        qc_checks.append(
            {
                "code": "LATE_PHOTO",
                "status": "warn",
                "value": effective_taken_at.isoformat(),
                "message": (
                    "Taken after the reporting deadline; " "still useful as supporting evidence."
                ),
            }
        )

    # GPS CHECKS
    if photo_lat is not None and photo_lng is not None:
        qc_checks.append(
            {
                "code": "GPS_PRESENT",
                "status": "pass",
                "value": f"{photo_lat},{photo_lng}",
                "message": "Location coordinates recorded.",
            }
        )

        if distance_m is not None:
            if distance_m <= GPS_WARN_M:
                qc_checks.append(
                    {
                        "code": "GPS_DISTANCE",
                        "status": "pass",
                        "value": distance_m,
                        "message": f"Photo taken at plot ({distance_m}m away).",
                    }
                )
            elif distance_m <= GPS_STRONG_WARN_M:
                qc_checks.append(
                    {
                        "code": "GPS_DISTANCE",
                        "status": "warn",
                        "value": distance_m,
                        "message": (
                            f"Photo location is {distance_m}m from the declared plot. "
                            "Verify your plot location."
                        ),
                    }
                )
            else:
                qc_checks.append(
                    {
                        "code": "GPS_DISTANCE",
                        "status": "warn",
                        "value": distance_m,
                        "message": (
                            f"Photo is {distance_m}m (>2 km) from the declared plot. "
                            "Retake at the field if possible."
                        ),
                    }
                )
    else:
        qc_checks.append(
            {
                "code": "GPS_PRESENT",
                "status": "warn",
                "value": None,
                "message": (
                    "No location on this photo. Turn on camera location "
                    "or retake with the app camera."
                ),
            }
        )

    # REUSED_PHOTO
    if is_reused_in_other_incident:
        qc_checks.append(
            {
                "code": "REUSED_PHOTO",
                "status": "warn",
                "value": True,
                "message": "This exact photo is already attached to another incident.",
            }
        )

    # Overall qc_status rollup: fail > warn > pass
    has_fail = any(c["status"] == "fail" for c in qc_checks)
    has_warn = any(c["status"] == "warn" for c in qc_checks)
    overall_status = "fail" if has_fail else ("warn" if has_warn else "pass")

    meta = {
        "width_px": width,
        "height_px": height,
        "size_bytes": len(image_bytes),
        "mime_type": "image/jpeg"
        if format_name in ("JPEG", "JPG")
        else ("image/png" if format_name == "PNG" else "image/webp"),
        "sha256": compute_sha256(image_bytes),
        "source": source,
        "shot_type": shot_type,
        "has_exif": exif_data.get("has_exif", False),
        "exif_taken_at": exif_data.get("taken_at").isoformat()
        if exif_data.get("taken_at")
        else None,
        "exif_gps_lat": exif_data.get("gps_lat"),
        "exif_gps_lng": exif_data.get("gps_lng"),
        "exif_make": exif_data.get("make"),
        "exif_model": exif_data.get("model"),
        "client_reported_at": client_reported_at.isoformat() if client_reported_at else None,
        "client_gps_lat": client_gps_lat if source == "camera_capture" else None,
        "client_gps_lng": client_gps_lng if source == "camera_capture" else None,
        "effective_taken_at": effective_taken_at.isoformat(),
        "time_basis": time_basis,
        "gps_basis": gps_basis,
        "distance_from_plot_m": distance_m,
        "qc_status": overall_status,
        "qc_checks": qc_checks,
    }

    return meta, display_bytes, thumb_bytes
