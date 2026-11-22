"""Evidence pack generation and download endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationError
from app.core.security import get_current_user
from app.db import get_supabase
from app.services.audit import write_audit_event
from app.services.checklist import compute_checklist
from app.services.report_pdf import generate_evidence_pdf, manifest_hash
from app.services.storage import (
    create_report_signed_url,
    create_signed_urls,
    upload_report_file,
)

router = APIRouter()


def _owned(sb, table: str, record_id: str, user_id: str) -> dict:
    result = sb.table(table).select("*").eq("id", record_id).eq("user_id", user_id).execute()
    if not result.data:
        raise NotFoundError()
    return result.data[0]


@router.post("/incidents/{incident_id}/reports", status_code=201)
async def create_report(incident_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    user_id = user["user_id"]
    incident = _owned(sb, "incidents", incident_id, user_id)

    photos_result = sb.table("photos").select("*").eq("incident_id", incident_id).execute()
    photos = photos_result.data
    for photo in photos:
        paths = {
            "display": photo["storage_path_display"],
            "thumb": photo["storage_path_thumb"],
        }
        photo["display_url"] = create_signed_urls(paths).get("display", "")

    intimations_result = (
        sb.table("intimation_records").select("*").eq("incident_id", incident_id).execute()
    )
    intimations = intimations_result.data
    weather_result = (
        sb.table("weather_snapshots")
        .select("*")
        .eq("incident_id", incident_id)
        .order("fetched_at", desc=True)
        .limit(1)
        .execute()
    )
    weather = weather_result.data[0] if weather_result.data else None

    checklist = compute_checklist(
        incident,
        photos,
        intimations,
        weather=weather,
    )

    profile_result = sb.table("profiles").select("*").eq("id", user_id).execute()
    profile = profile_result.data[0] if profile_result.data else {"full_name": "Farmer"}

    existing = (
        sb.table("reports")
        .select("version")
        .eq("incident_id", incident_id)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    version = int(existing.data[0]["version"]) + 1 if existing.data else 1

    pdf_bytes, pdf_hash = generate_evidence_pdf(
        incident=incident,
        profile=profile,
        photos=photos,
        intimations=intimations,
        weather=weather,
        checklist=checklist,
        version=version,
    )
    storage_path = f"{user_id}/{incident_id}/reports/v{version}.pdf"
    upload_report_file(storage_path, pdf_bytes)
    manifest = manifest_hash(incident_id, photos)
    generated_at = datetime.now(timezone.utc).isoformat()

    row = {
        "incident_id": incident_id,
        "user_id": user_id,
        "version": version,
        "storage_path": storage_path,
        "sha256": pdf_hash,
        "size_bytes": len(pdf_bytes),
        "completeness": checklist["completeness"],
        "photo_count": len(photos),
        "manifest_hash": manifest,
        "generated_from": {
            "photo_ids": [str(photo["id"]) for photo in photos],
            "checklist": checklist,
        },
        "generated_at": generated_at,
    }
    result = sb.table("reports").insert(row).execute()
    report = result.data[0]
    write_audit_event(
        sb,
        incident_id,
        user_id,
        "report_generated",
        {
            "report_id": report["id"],
            "version": version,
            "sha256": pdf_hash,
            "manifest_hash": manifest,
        },
    )

    signed = create_report_signed_url(storage_path)
    return {
        "id": str(report["id"]),
        "version": version,
        "generated_at": generated_at,
        "completeness": checklist["completeness"],
        "photo_count": len(photos),
        "size_bytes": len(pdf_bytes),
        "sha256": pdf_hash,
        "download": {
            "url": signed,
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(seconds=get_settings().signed_url_ttl_seconds)
            )
            .replace(microsecond=0)
            .isoformat(),
        },
    }


@router.get("/incidents/{incident_id}/reports")
async def list_reports(incident_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    _owned(sb, "incidents", incident_id, user["user_id"])
    result = (
        sb.table("reports")
        .select("*")
        .eq("incident_id", incident_id)
        .order("version", desc=True)
        .execute()
    )
    return result.data


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    report = _owned(sb, "reports", report_id, user["user_id"])
    signed = create_report_signed_url(report["storage_path"])
    if not signed:
        raise ValidationError("Report download is temporarily unavailable.")
    write_audit_event(
        sb,
        report["incident_id"],
        user["user_id"],
        "report_downloaded",
        {
            "report_id": report_id,
        },
    )
    return {
        "url": signed,
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=get_settings().signed_url_ttl_seconds)
        )
        .replace(microsecond=0)
        .isoformat(),
    }
