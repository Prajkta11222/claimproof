import io

import numpy as np
from PIL import Image, ImageFilter

from app.services.exif import extract_exif
from app.services.photo_qc import (
    calculate_blur_laplacian,
    calculate_luminance,
    haversine_distance_m,
    process_and_qc_image,
)


def _jpeg(color=(120, 120, 120), width=700, height=500):
    image = Image.new("RGB", (width, height), color)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_haversine_distance_is_zero_for_same_point():
    assert haversine_distance_m(21.1458, 79.0882, 21.1458, 79.0882) == 0.0


def test_haversine_distance_detects_nearby_plot():
    distance = haversine_distance_m(21.1458, 79.0882, 21.1465, 79.0890)
    assert 110 <= distance <= 140


def test_blur_and_luminance_calculations():
    sharp = Image.fromarray(
        np.tile(np.array([[[0, 0, 0], [255, 255, 255]]], dtype=np.uint8), (500, 350, 1)),
        "RGB",
    ).convert("L")
    blurred = sharp.filter(ImageFilter.GaussianBlur(radius=12))

    assert calculate_blur_laplacian(sharp) > calculate_blur_laplacian(blurred)
    assert calculate_luminance(Image.new("L", (10, 10), 50)) == 50.0


def test_process_qc_generates_display_thumb_and_resolution_check():
    image_bytes = _jpeg()
    incident = {
        "event_occurred_at": "2026-11-20T10:00:00+00:00",
        "reporting_deadline_at": "2026-11-23T10:00:00+00:00",
        "location_lat": 21.1458,
        "location_lng": 79.0882,
    }

    metadata, display, thumb = process_and_qc_image(
        image_bytes=image_bytes,
        source="gallery_upload",
        shot_type="wide",
        incident=incident,
        exif_data={"has_exif": False, "taken_at": None, "gps_lat": None, "gps_lng": None},
        client_reported_at=None,
        client_gps_lat=None,
        client_gps_lng=None,
    )

    assert metadata["qc_status"] in {"pass", "warn", "fail"}
    assert metadata["mime_type"] == "image/jpeg"
    assert metadata["time_basis"] == "upload"
    assert metadata["gps_basis"] is None
    assert Image.open(io.BytesIO(display)).format == "JPEG"
    assert Image.open(io.BytesIO(thumb)).format == "JPEG"


def test_process_qc_rejects_corrupt_image():
    incident = {
        "event_occurred_at": "2026-11-20T10:00:00+00:00",
        "reporting_deadline_at": "2026-11-23T10:00:00+00:00",
        "location_lat": 21.1458,
        "location_lng": 79.0882,
    }

    try:
        process_and_qc_image(
            image_bytes=b"not an image",
            source="gallery_upload",
            shot_type="wide",
            incident=incident,
            exif_data={"has_exif": False},
            client_reported_at=None,
            client_gps_lat=None,
            client_gps_lng=None,
        )
    except Exception:
        assert True
    else:
        assert False, "Corrupt images must be rejected"


def test_extract_exif_fails_soft_for_corrupt_bytes():
    assert extract_exif(b"not an image")["has_exif"] is False
