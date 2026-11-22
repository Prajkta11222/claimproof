"""Photo upload and management endpoints (SPEC §7.1, §9)."""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile

from app.core.config import get_settings
from app.core.errors import (
    DuplicatePhotoError,
    NotFoundError,
    PayloadTooLargeError,
    PhotoLimitError,
    UnsupportedMediaError,
    ValidationError,
)
from app.core.rules import MAX_PHOTOS_PER_INCIDENT, MAX_UPLOAD_BYTES, UPLOAD_CONCURRENCY
from app.core.security import get_current_user
from app.db import get_supabase
from app.schemas.photos import PhotoPatchRequest, PhotoResponse, PhotoUrls, QcCheck
from app.services.ai_qc import analyze_photo_bytes, apply_ai_signals
from app.services.audit import write_audit_event
from app.services.exif import extract_exif
from app.services.photo_qc import compute_sha256, process_and_qc_image
from app.services.storage import (
    create_signed_urls,
    delete_photo_files,
    get_storage_paths,
    upload_photo_files,
)

router = APIRouter()

# Semaphore to cap concurrent image processing in RAM (SPEC §7.3, NFR-6)
upload_semaphore = threading.BoundedSemaphore(UPLOAD_CONCURRENCY)


@router.post("/incidents/{incident_id}/photos", response_model=PhotoResponse, status_code=201)
async def upload_photo(
    incident_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source: str = Form(...),
    shot_type: str = Form("other"),
    client_reported_at: Optional[str] = Form(None),
    client_gps_lat: Optional[float] = Form(None),
    client_gps_lng: Optional[float] = Form(None),
    client_gps_accuracy_m: Optional[float] = Form(None),
    user: dict = Depends(get_current_user),
):
    """Upload one crop photo, compute SHA-256, extract EXIF, and run deterministic QC."""
    sb = get_supabase()
    user_id = user["user_id"]

    # 1. Authz: incident belongs to user and is open
    incident = _get_owned_incident(sb, incident_id, user_id)
    if incident["status"] != "open":
        raise ValidationError("Cannot add photos to an archived incident.")

    # Check photo limit (max 12 per incident, SPEC §5.5)
    existing_photos = (
        sb.table("photos").select("id, sha256").eq("incident_id", incident_id).execute()
    )
    if len(existing_photos.data) >= MAX_PHOTOS_PER_INCIDENT:
        raise PhotoLimitError(
            f"Maximum limit of {MAX_PHOTOS_PER_INCIDENT} photos reached for this incident."
        )

    # 2. Stream bytes with a hard cap before and during reads
    content_length = getattr(file, "size", None)
    if content_length is not None and content_length > MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError("File exceeds 12 MB limit.")

    chunks: list[bytes] = []
    bytes_read = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        bytes_read += len(chunk)
        if bytes_read > MAX_UPLOAD_BYTES:
            raise PayloadTooLargeError("File exceeds 12 MB limit.")
        chunks.append(chunk)
    contents = b"".join(chunks)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError("File exceeds 12 MB limit.")

    if len(contents) == 0:
        raise ValidationError("Uploaded file is empty.")

    # Validate source and shot_type
    if source not in ("camera_capture", "gallery_upload"):
        raise ValidationError("Source must be 'camera_capture' or 'gallery_upload'.")
    if shot_type not in ("wide", "close_up", "document", "other"):
        shot_type = "other"

    # Parse client_reported_at
    parsed_client_time = None
    if client_reported_at:
        try:
            parsed_client_time = datetime.fromisoformat(client_reported_at)
            if parsed_client_time.tzinfo is None:
                parsed_client_time = parsed_client_time.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    # 3. Compute exact SHA-256 of uploaded bytes
    photo_hash = compute_sha256(contents)

    # 4. Duplicate checks
    for p in existing_photos.data:
        if p["sha256"] == photo_hash:
            raise DuplicatePhotoError(
                "This exact photo has already been uploaded to this incident.",
                details=[
                    {"field": "file", "issue": "duplicate_sha256", "existing_photo_id": p["id"]}
                ],
            )

    # Cross-incident reuse check for same user
    other_incident_photos = (
        sb.table("photos")
        .select("id")
        .eq("user_id", user_id)
        .eq("sha256", photo_hash)
        .neq("incident_id", incident_id)
        .execute()
    )
    is_reused = len(other_incident_photos.data) > 0

    # 5. Decode with Pillow & Run QC under concurrency semaphore
    acquired = upload_semaphore.acquire(blocking=True, timeout=15)
    if not acquired:
        raise ValidationError("Server busy processing uploads. Please retry in a moment.")

    try:
        exif_data = extract_exif(contents)
        meta, display_bytes, thumb_bytes = process_and_qc_image(
            image_bytes=contents,
            source=source,
            shot_type=shot_type,
            incident=incident,
            exif_data=exif_data,
            client_reported_at=parsed_client_time,
            client_gps_lat=client_gps_lat,
            client_gps_lng=client_gps_lng,
            is_reused_in_other_incident=is_reused,
        )
    except ValueError as e:
        raise UnsupportedMediaError(str(e))
    except Exception as e:
        raise ValidationError(f"Could not read image: {e}")
    finally:
        upload_semaphore.release()

    # 6. Upload original, display, and thumb to storage
    photo_id = str(uuid.uuid4())
    ext = (
        "png"
        if meta["mime_type"] == "image/png"
        else ("webp" if meta["mime_type"] == "image/webp" else "jpg")
    )
    paths = get_storage_paths(user_id, incident_id, photo_id, ext=ext)

    try:
        upload_photo_files(
            paths=paths,
            original_bytes=contents,
            display_bytes=display_bytes,
            thumb_bytes=thumb_bytes,
            original_mime=meta["mime_type"],
        )
    except Exception as e:
        raise ValidationError(f"Storage upload failed: {e}")

    # 7. Insert DB row
    now_iso = datetime.now(timezone.utc).isoformat()
    db_row = {
        "id": photo_id,
        "incident_id": incident_id,
        "user_id": user_id,
        "storage_path_original": paths["original"],
        "storage_path_display": paths["display"],
        "storage_path_thumb": paths["thumb"],
        "original_filename": file.filename[:200] if file.filename else None,
        "mime_type": meta["mime_type"],
        "size_bytes": meta["size_bytes"],
        "width_px": meta["width_px"],
        "height_px": meta["height_px"],
        "sha256": meta["sha256"],
        "source": meta["source"],
        "shot_type": meta["shot_type"],
        "exif_taken_at": meta["exif_taken_at"],
        "exif_gps_lat": meta["exif_gps_lat"],
        "exif_gps_lng": meta["exif_gps_lng"],
        "exif_make": meta["exif_make"],
        "exif_model": meta["exif_model"],
        "has_exif": meta["has_exif"],
        "client_reported_at": meta["client_reported_at"],
        "client_gps_lat": meta["client_gps_lat"],
        "client_gps_lng": meta["client_gps_lng"],
        "client_gps_accuracy_m": client_gps_accuracy_m,
        "effective_taken_at": meta["effective_taken_at"],
        "time_basis": meta["time_basis"],
        "gps_basis": meta["gps_basis"],
        "distance_from_plot_m": meta["distance_from_plot_m"],
        "uploaded_at": now_iso,
        "qc_status": meta["qc_status"],
        "qc_checks": meta["qc_checks"],
        "ai_status": "skipped" if shot_type == "document" else "pending",
        "created_at": now_iso,
    }

    insert_res = sb.table("photos").insert(db_row).execute()
    created_record = insert_res.data[0]

    # 8. Audit event
    write_audit_event(
        sb,
        incident_id,
        user_id,
        "photo_uploaded",
        {
            "photo_id": photo_id,
            "sha256": meta["sha256"],
            "qc_status": meta["qc_status"],
            "shot_type": meta["shot_type"],
        },
    )

    signed_urls = create_signed_urls(paths)
    if meta["shot_type"] != "document":
        background_tasks.add_task(
            _run_ai_analysis,
            sb,
            created_record,
            incident,
            display_bytes,
        )
    return _row_to_photo_response(created_record, signed_urls)


@router.get("/incidents/{incident_id}/photos", response_model=list[PhotoResponse])
async def list_incident_photos(
    incident_id: str,
    user: dict = Depends(get_current_user),
):
    """List all photos for an incident with signed thumbnail and display URLs."""
    sb = get_supabase()
    user_id = user["user_id"]
    _get_owned_incident(sb, incident_id, user_id)

    result = (
        sb.table("photos")
        .select("*")
        .eq("incident_id", incident_id)
        .order("uploaded_at", desc=False)
        .execute()
    )

    items: list[PhotoResponse] = []
    for row in result.data:
        paths = {
            "original": row["storage_path_original"],
            "display": row["storage_path_display"],
            "thumb": row["storage_path_thumb"],
        }
        signed = create_signed_urls(paths)
        items.append(_row_to_photo_response(row, signed))

    return items


@router.get("/photos/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: str,
    user: dict = Depends(get_current_user),
):
    """Get single photo detail with fresh signed URLs and AI status."""
    sb = get_supabase()
    user_id = user["user_id"]
    row = _get_owned_photo(sb, photo_id, user_id)

    paths = {
        "original": row["storage_path_original"],
        "display": row["storage_path_display"],
        "thumb": row["storage_path_thumb"],
    }
    signed = create_signed_urls(paths)
    return _row_to_photo_response(row, signed)


@router.post("/photos/{photo_id}/analyze", response_model=PhotoResponse)
async def analyze_photo(
    photo_id: str,
    user: dict = Depends(get_current_user),
):
    """Retry advisory Gemini analysis, capped at three attempts."""
    sb = get_supabase()
    user_id = user["user_id"]
    row = _get_owned_photo(sb, photo_id, user_id)

    if row.get("shot_type") == "document":
        raise ValidationError("Document photos are skipped by AI analysis.")
    settings = get_settings()
    if int(row.get("ai_attempts") or 0) >= settings.ai_max_attempts_per_photo:
        raise ValidationError("Maximum AI analysis attempts reached.")

    incident_result = (
        sb.table("incidents")
        .select("*")
        .eq("id", row["incident_id"])
        .eq("user_id", user_id)
        .execute()
    )
    if not incident_result.data:
        raise NotFoundError()

    paths = {
        "original": row["storage_path_original"],
        "display": row["storage_path_display"],
        "thumb": row["storage_path_thumb"],
    }
    signed = create_signed_urls(paths)
    display_url = signed.get("display")
    display_bytes = b""
    if display_url:
        try:
            import httpx

            response = httpx.get(display_url, timeout=20)
            response.raise_for_status()
            display_bytes = response.content
        except Exception:
            display_bytes = b""

    if not display_bytes:
        raise ValidationError("Could not retrieve the display image for analysis.")

    await _run_ai_analysis_async(
        sb,
        row,
        incident_result.data[0],
        display_bytes,
    )

    updated = _get_owned_photo(sb, photo_id, user_id)
    fresh_signed = create_signed_urls(paths)
    return _row_to_photo_response(updated, fresh_signed)


@router.patch("/photos/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    photo_id: str,
    body: PhotoPatchRequest,
    user: dict = Depends(get_current_user),
):
    """Update photo shot_type."""
    sb = get_supabase()
    user_id = user["user_id"]
    _get_owned_photo(sb, photo_id, user_id)

    res = (
        sb.table("photos")
        .update({"shot_type": body.shot_type})
        .eq("id", photo_id)
        .eq("user_id", user_id)
        .execute()
    )

    row = res.data[0]
    paths = {
        "original": row["storage_path_original"],
        "display": row["storage_path_display"],
        "thumb": row["storage_path_thumb"],
    }
    signed = create_signed_urls(paths)
    return _row_to_photo_response(row, signed)


@router.delete("/photos/{photo_id}", status_code=204)
async def delete_photo(
    photo_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a photo and remove its files from storage."""
    sb = get_supabase()
    user_id = user["user_id"]
    row = _get_owned_photo(sb, photo_id, user_id)

    # 1. Delete from storage
    paths = {
        "original": row.get("storage_path_original"),
        "display": row.get("storage_path_display"),
        "thumb": row.get("storage_path_thumb"),
    }
    delete_photo_files(paths)

    # 2. Audit event keeps its hash (SPEC §6.4, §7.1)
    write_audit_event(
        sb,
        row["incident_id"],
        user_id,
        "photo_deleted",
        {
            "photo_id": photo_id,
            "sha256": row["sha256"],
        },
    )

    # 3. Delete from DB
    sb.table("photos").delete().eq("id", photo_id).eq("user_id", user_id).execute()
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_owned_incident(sb, incident_id: str, user_id: str) -> dict:
    res = sb.table("incidents").select("*").eq("id", incident_id).eq("user_id", user_id).execute()
    if not res.data:
        raise NotFoundError("Incident not found.")
    return res.data[0]


def _get_owned_photo(sb, photo_id: str, user_id: str) -> dict:
    res = sb.table("photos").select("*").eq("id", photo_id).eq("user_id", user_id).execute()
    if not res.data:
        raise NotFoundError("Photo not found.")
    return res.data[0]


def _row_to_photo_response(row: dict, urls: dict[str, str]) -> PhotoResponse:
    checks = []
    for c in row.get("qc_checks") or []:
        checks.append(
            QcCheck(
                code=c["code"],
                status=c["status"],
                value=c.get("value"),
                message=c.get("message", ""),
            )
        )

    return PhotoResponse(
        id=str(row["id"]),
        incident_id=str(row["incident_id"]),
        user_id=str(row["user_id"]),
        sha256=str(row["sha256"]),
        source=row["source"],
        shot_type=row["shot_type"],
        width_px=row["width_px"],
        height_px=row["height_px"],
        size_bytes=row["size_bytes"],
        mime_type=row["mime_type"],
        has_exif=bool(row.get("has_exif", False)),
        effective_taken_at=str(row["effective_taken_at"]),
        time_basis=row["time_basis"],
        gps_basis=row.get("gps_basis"),
        distance_from_plot_m=float(row["distance_from_plot_m"])
        if row.get("distance_from_plot_m") is not None
        else None,
        qc_status=row["qc_status"],
        qc_checks=checks,
        ai_status=row.get("ai_status", "pending"),
        ai_attempts=int(row.get("ai_attempts") or 0),
        ai_result=row.get("ai_result"),
        uploaded_at=str(row["uploaded_at"]),
        created_at=str(row["created_at"]),
        urls=PhotoUrls(thumb=urls.get("thumb", ""), display=urls.get("display", "")),
    )


def _run_ai_analysis(sb, row: dict, incident: dict, display_bytes: bytes) -> None:
    """Background-task wrapper."""
    asyncio.run(_run_ai_analysis_async(sb, row, incident, display_bytes))


async def _run_ai_analysis_async(sb, row: dict, incident: dict, display_bytes: bytes) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    attempts = int(row.get("ai_attempts") or 0) + 1
    if not settings.ai_enabled:
        sb.table("photos").update(
            {
                "ai_status": "skipped",
                "ai_attempts": attempts,
            }
        ).eq("id", row["id"]).execute()
        return

    try:
        ai_result = await analyze_photo_bytes(
            display_bytes,
            incident["crop_name"],
            incident["incident_type"],
        )
        existing = sb.table("photos").select("qc_checks,qc_status").eq("id", row["id"]).execute()
        current = existing.data[0] if existing.data else row
        checks = apply_ai_signals(
            current.get("qc_checks") or [],
            ai_result,
            incident["crop_name"],
            row["shot_type"],
        )
        statuses = {check["status"] for check in checks}
        qc_status = "fail" if "fail" in statuses else ("warn" if "warn" in statuses else "pass")
        sb.table("photos").update(
            {
                "ai_status": "done",
                "ai_attempts": attempts,
                "ai_model": settings.gemini_model,
                "ai_result": ai_result,
                "qc_checks": checks,
                "qc_status": qc_status,
            }
        ).eq("id", row["id"]).execute()
    except Exception:
        sb.table("photos").update(
            {
                "ai_status": "failed",
                "ai_attempts": attempts,
            }
        ).eq("id", row["id"]).execute()
