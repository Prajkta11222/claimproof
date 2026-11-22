"""ReportLab evidence pack generation (SPEC section 13)."""

from __future__ import annotations

import io
from xml.sax.saxutils import escape

import httpx
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as PdfImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table


def manifest_hash(incident_id: str, photos: list[dict]) -> str:
    import hashlib

    sorted_hashes = sorted(str(photo["sha256"]) for photo in photos)
    payload = incident_id + "\n" + "\n".join(sorted_hashes)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_evidence_pdf(
    incident: dict,
    profile: dict,
    photos: list[dict],
    intimations: list[dict],
    weather: dict | None,
    checklist: dict,
    version: int,
) -> tuple[bytes, str]:
    import hashlib

    manifest = manifest_hash(str(incident["id"]), photos)
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm)
    story = []

    completeness = checklist["completeness"].upper()
    story.append(Paragraph("ClaimProof Evidence Pack", styles["Title"]))
    story.append(
        Paragraph(
            f"Incident {escape(str(incident['id'])[:8])} | Version {version} | "
            f"<b>{completeness}</b>",
            styles["Heading2"],
        )
    )
    story.append(Paragraph(f"Manifest hash: {escape(manifest)}", styles["Code"]))
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "Prepared with ClaimProof from information entered by the farmer. "
            "Not an official insurer or government document. "
            "Does not guarantee any claim outcome.",
            styles["BodyText"],
        )
    )

    story.append(Paragraph("Farmer and Plot", styles["Heading2"]))
    story.append(
        Table(
            [
                ["Name", escape(str(profile.get("full_name") or "Farmer"))],
                [
                    "Location",
                    escape(
                        ", ".join(
                            filter(
                                None,
                                [
                                    incident.get("village"),
                                    incident.get("taluka"),
                                    incident.get("district"),
                                    incident.get("state"),
                                ],
                            )
                        )
                    ),
                ],
                ["Plot coordinates", f"{incident['location_lat']}, {incident['location_lng']}"],
                ["Crop", escape(str(incident.get("crop_name") or ""))],
                ["Survey number", escape(str(incident.get("survey_number") or "Not provided"))],
                [
                    "Affected area",
                    escape(str(incident.get("area_affected_acres") or "Not provided")),
                ],
                ["Scheme", escape(str(incident.get("scheme") or ""))],
                [
                    "Policy reference",
                    escape(str(incident.get("policy_reference") or "Not provided")),
                ],
            ],
            colWidths=[35 * mm, 125 * mm],
        )
    )

    story.append(Paragraph("Incident and Timeline", styles["Heading2"]))
    incident_rows = [
        ["Type", escape(str(incident["incident_type"]))],
        ["Description", escape(str(incident.get("description") or "Not provided"))],
        ["Event time", escape(str(incident["event_occurred_at"]))],
        ["Reporting deadline", escape(str(incident["reporting_deadline_at"]))],
    ]
    for intimation in intimations:
        incident_rows.append(
            [
                "Intimation",
                escape(
                    f"{intimation.get('channel')} | {intimation.get('intimated_at')} | "
                    f"{intimation.get('reference_number') or 'No reference'}"
                ),
            ]
        )
    story.append(Table(incident_rows, colWidths=[35 * mm, 125 * mm]))

    story.append(Paragraph("Completeness", styles["Heading2"]))
    checklist_rows = [["Item", "Severity", "Status"]]
    for item in checklist["items"]:
        checklist_rows.append(
            [
                escape(item["label"]),
                escape(item["severity"]),
                escape(item["status"]),
            ]
        )
    story.append(Table(checklist_rows, colWidths=[105 * mm, 30 * mm, 25 * mm], repeatRows=1))

    story.append(Paragraph("Photo Evidence", styles["Heading2"]))
    for index, photo in enumerate(sorted(photos, key=lambda row: str(row["effective_taken_at"]))):
        story.append(
            Paragraph(
                f"Photo {index + 1} of {len(photos)}",
                styles["Heading3"],
            )
        )
        display_url = photo.get("display_url")
        if display_url:
            try:
                response = httpx.get(display_url, timeout=10)
                response.raise_for_status()
                source = io.BytesIO(response.content)
                with Image.open(source) as image:
                    image.thumbnail((900, 900), Image.Resampling.LANCZOS)
                    rendered = io.BytesIO()
                    image.convert("RGB").save(rendered, format="JPEG", quality=80)
                    rendered.seek(0)
                    story.append(
                        PdfImage(rendered, width=120 * mm, height=90 * mm, kind="proportional")
                    )
            except Exception:
                story.append(Paragraph("Photo image unavailable.", styles["Italic"]))
        story.append(
            Paragraph(
                f"<b>Shot type:</b> {escape(str(photo['shot_type']))}<br/>"
                f"<b>Time:</b> {escape(str(photo['effective_taken_at']))} "
                f"(basis: {escape(str(photo['time_basis']))})<br/>"
                f"<b>Location:</b> {escape(str(photo.get('gps_basis') or 'none'))} "
                f"| distance: {escape(str(photo.get('distance_from_plot_m') or 'unknown'))} m<br/>"
                f"<b>QC:</b> {escape(str(photo['qc_status']))}<br/>"
                f"<b>SHA-256:</b> {escape(str(photo['sha256']))}",
                styles["BodyText"],
            )
        )
        ai_result = photo.get("ai_result")
        if ai_result:
            observation = escape(
                str(ai_result.get("description") or ai_result.get("damage_notes") or "")
            )
            tips = ai_result.get("retake_suggestions") or []
            story.append(
                Paragraph(
                    f"<b>AI observations - may be wrong:</b> {observation}"
                    + (
                        f"<br/>Retake tips: {escape('; '.join(str(tip) for tip in tips))}"
                        if tips
                        else ""
                    ),
                    styles["Italic"],
                )
            )

    story.append(Paragraph("Weather Context", styles["Heading2"]))
    if weather:
        summary = weather.get("summary") or {}
        story.append(
            Paragraph(
                f"Total precipitation: {summary.get('total_precip_mm', 0)} mm; "
                f"max gust: {summary.get('max_gust_kmh', 0)} km/h",
                styles["BodyText"],
            )
        )
    else:
        story.append(Paragraph("Weather unavailable.", styles["BodyText"]))
    story.append(Paragraph("Weather data by Open-Meteo.com (CC BY 4.0).", styles["BodyText"]))
    story.append(
        Paragraph(
            "Model data for a wide area (several km). "
            "It cannot confirm what happened on your plot.",
            styles["Italic"],
        )
    )

    story.append(Paragraph("Integrity and Limitations", styles["Heading2"]))
    story.append(
        Paragraph(
            "A photo hash verifies that exact original bytes have not changed, not that the scene "
            "was not staged or that the claim is valid. "
            "AI/quality results are assistive and do not "
            "prove an event or loss.",
            styles["BodyText"],
        )
    )
    story.append(
        Paragraph(
            "Self-reported fields: incident time, plot, crop, area, and intimations.",
            styles["BodyText"],
        )
    )
    story.append(
        Paragraph(
            "Deadline assumptions: A1 (earliest possible time for date-only events) "
            "and A2 (72-hour rule).",
            styles["BodyText"],
        )
    )

    story.append(Paragraph("Appendix", styles["Heading2"]))
    story.append(
        Paragraph(
            "Manifest formula: incident_id + newline + sorted photo SHA-256 values.",
            styles["Code"],
        )
    )
    for photo in sorted(photos, key=lambda row: str(row["sha256"])):
        story.append(Paragraph(escape(str(photo["sha256"])), styles["Code"]))

    document.build(story)
    pdf_bytes = buffer.getvalue()
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    return pdf_bytes, sha256
