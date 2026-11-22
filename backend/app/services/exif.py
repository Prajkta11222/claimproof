"""EXIF extraction service (SPEC §9.2, §9.4)."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from PIL import ExifTags, Image

IST = ZoneInfo("Asia/Kolkata")


def _convert_to_degrees(value: Any) -> float | None:
    """Convert the GPS coordinates stored in EXIF to decimal degrees."""
    try:
        if isinstance(value, (tuple, list)) and len(value) == 3:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        pass
    return None


def extract_exif(image_bytes: bytes) -> dict[str, Any]:
    """Extract EXIF data: DateTimeOriginal, GPS lat/lng, make, model, orientation.

    Applies IST timezone fallback per Assumption A14 if OffsetTimeOriginal is absent.
    """
    result: dict[str, Any] = {
        "has_exif": False,
        "taken_at": None,
        "gps_lat": None,
        "gps_lng": None,
        "make": None,
        "model": None,
        "orientation": 1,
    }

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            exif_raw = img.getexif()
            if not exif_raw:
                return result

            result["has_exif"] = True

            # Standard tags
            for tag_id, value in exif_raw.items():
                tag_name = ExifTags.TAGS.get(tag_id)
                if tag_name == "Make" and isinstance(value, str):
                    result["make"] = value.strip()[:60]
                elif tag_name == "Model" and isinstance(value, str):
                    result["model"] = value.strip()[:60]
                elif tag_name == "Orientation" and isinstance(value, int):
                    result["orientation"] = value

            # Exif IFD sub-table
            exif_ifd = exif_raw.get_ifd(ExifTags.IFD.Exif)
            if exif_ifd:
                date_str = exif_ifd.get(ExifTags.Base.DateTimeOriginal) or exif_ifd.get(
                    ExifTags.Base.DateTimeDigitized
                )
                offset_str = exif_ifd.get(0x9011)  # OffsetTimeOriginal

                if date_str and isinstance(date_str, str):
                    try:
                        # Common format: "YYYY:MM:DD HH:MM:SS"
                        parsed_dt = datetime.strptime(date_str.strip()[:19], "%Y:%m:%d %H:%M:%S")
                        if offset_str and isinstance(offset_str, str):
                            # e.g., "+05:30"
                            try:
                                offset_parts = offset_str.strip().split(":")
                                hours = int(offset_parts[0])
                                minutes = int(offset_parts[1]) if len(offset_parts) > 1 else 0
                                sign = 1 if hours >= 0 else -1
                                tz = timezone(
                                    sign
                                    * __import__("datetime").timedelta(
                                        hours=abs(hours), minutes=minutes
                                    )
                                )
                                parsed_dt = parsed_dt.replace(tzinfo=tz)
                            except Exception:
                                parsed_dt = parsed_dt.replace(tzinfo=IST)
                        else:
                            # A14: assume IST if offset absent
                            parsed_dt = parsed_dt.replace(tzinfo=IST)

                        result["taken_at"] = parsed_dt.astimezone(timezone.utc)
                    except Exception:
                        pass

            # GPS IFD sub-table
            gps_ifd = exif_raw.get_ifd(ExifTags.IFD.GPSInfo)
            if gps_ifd:
                gps_lat = gps_ifd.get(ExifTags.GPS.GPSLatitude)
                gps_lat_ref = gps_ifd.get(ExifTags.GPS.GPSLatitudeRef)
                gps_lng = gps_ifd.get(ExifTags.GPS.GPSLongitude)
                gps_lng_ref = gps_ifd.get(ExifTags.GPS.GPSLongitudeRef)

                if gps_lat and gps_lat_ref and gps_lng and gps_lng_ref:
                    lat_deg = _convert_to_degrees(gps_lat)
                    lng_deg = _convert_to_degrees(gps_lng)

                    if lat_deg is not None and lng_deg is not None:
                        if str(gps_lat_ref).upper() == "S":
                            lat_deg = -lat_deg
                        if str(gps_lng_ref).upper() == "W":
                            lng_deg = -lng_deg

                        if -90 <= lat_deg <= 90 and -180 <= lng_deg <= 180:
                            result["gps_lat"] = round(lat_deg, 6)
                            result["gps_lng"] = round(lng_deg, 6)

    except Exception:
        # Malformed EXIF must fail soft
        pass

    return result
