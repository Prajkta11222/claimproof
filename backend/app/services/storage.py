"""Supabase Storage service wrapper (SPEC §6.3, §14.1)."""

from __future__ import annotations

from app.core.config import get_settings
from app.db import get_supabase


def _bucket_name() -> str:
    return get_settings().supabase_storage_bucket


def get_storage_paths(
    user_id: str, incident_id: str, photo_id: str, ext: str = "jpg"
) -> dict[str, str]:
    """Generate deterministic storage paths using UUIDs only (SPEC §6.3)."""
    base = f"{user_id}/{incident_id}/photos/{photo_id}"
    return {
        "original": f"{base}/original.{ext}",
        "display": f"{base}/display.jpg",
        "thumb": f"{base}/thumb.jpg",
    }


def upload_photo_files(
    paths: dict[str, str],
    original_bytes: bytes,
    display_bytes: bytes,
    thumb_bytes: bytes,
    original_mime: str,
) -> None:
    """Upload original, display, and thumb images to private bucket."""
    sb = get_supabase()
    bucket = sb.storage.from_(_bucket_name())

    # 1. Original
    bucket.upload(
        path=paths["original"],
        file=original_bytes,
        file_options={"content-type": original_mime, "upsert": "true"},
    )

    # 2. Display
    bucket.upload(
        path=paths["display"],
        file=display_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )

    # 3. Thumb
    bucket.upload(
        path=paths["thumb"],
        file=thumb_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )


def create_signed_urls(paths: dict[str, str], ttl_seconds: int | None = None) -> dict[str, str]:
    """Generate short-lived signed URLs for display and thumb images."""
    if ttl_seconds is None:
        ttl_seconds = get_settings().signed_url_ttl_seconds
    sb = get_supabase()
    bucket = sb.storage.from_(_bucket_name())

    res: dict[str, str] = {}
    try:
        display_res = bucket.create_signed_url(paths["display"], ttl_seconds)
        res["display"] = display_res.get("signedURL") or display_res.get("signedUrl") or ""
    except Exception:
        res["display"] = ""

    try:
        thumb_res = bucket.create_signed_url(paths["thumb"], ttl_seconds)
        res["thumb"] = thumb_res.get("signedURL") or thumb_res.get("signedUrl") or ""
    except Exception:
        res["thumb"] = ""

    return res


def delete_photo_files(paths: dict[str, str]) -> None:
    """Delete all files associated with a photo from storage."""
    sb = get_supabase()
    bucket = sb.storage.from_(_bucket_name())
    file_list = [p for p in paths.values() if p]
    if file_list:
        try:
            bucket.remove(file_list)
        except Exception:
            pass


def upload_report_file(storage_path: str, pdf_bytes: bytes) -> None:
    sb = get_supabase()
    sb.storage.from_(_bucket_name()).upload(
        path=storage_path,
        file=pdf_bytes,
        file_options={"content-type": "application/pdf", "upsert": "false"},
    )


def create_report_signed_url(storage_path: str, ttl_seconds: int | None = None) -> str:
    if ttl_seconds is None:
        ttl_seconds = get_settings().signed_url_ttl_seconds
    sb = get_supabase()
    try:
        result = sb.storage.from_(_bucket_name()).create_signed_url(storage_path, ttl_seconds)
        return result.get("signedURL") or result.get("signedUrl") or ""
    except Exception:
        return ""
