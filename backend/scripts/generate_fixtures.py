"""Generate synthetic image fixtures from Pillow (no real farmer data)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import piexif
from PIL import Image, ImageDraw, ImageFilter

OUTPUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "images"


def base_image(width: int = 1600, height: int = 1200, luminance: int = 145) -> Image.Image:
    pixels = np.full((height, width, 3), luminance, dtype=np.uint8)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 12, (height, width, 3))
    pixels = np.clip(pixels + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(pixels, "RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, int(height * 0.45), width, height), fill=(52, 120, 45))
    for x in range(100, width, 180):
        draw.line((x, int(height * 0.65), x + 30, height), fill=(30, 75, 30), width=12)
    return image


def add_exif(image: Image.Image, lat: float, lng: float, date: str) -> Image.Image:
    exif = {
        "0th": {piexif.ImageIFD.Make: b"ClaimProof", piexif.ImageIFD.Model: b"Synthetic"},
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: date.encode(),
            piexif.ExifIFD.OffsetTimeOriginal: b"+05:30",
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
            piexif.GPSIFD.GPSLatitude: ((int(abs(lat)), 1), (0, 1), (0, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b"E" if lng >= 0 else b"W",
            piexif.GPSIFD.GPSLongitude: ((int(abs(lng)), 1), (0, 1), (0, 1)),
        },
        "1st": {},
        "thumbnail": None,
    }
    image.info["exif"] = piexif.dump(exif)
    return image


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sharp = base_image()
    sharp.save(OUTPUT / "sharp.jpg", exif=sharp.info.get("exif", b""))
    sharp.filter(ImageFilter.GaussianBlur(radius=8)).save(OUTPUT / "blurred.jpg")
    base_image(luminance=18).save(OUTPUT / "very_dark.jpg")
    base_image(luminance=235).save(OUTPUT / "very_bright.jpg")
    base_image(width=300, height=225).save(OUTPUT / "tiny.jpg")

    near = add_exif(base_image(), 21.145800, 79.088200, "2026:11:21 16:30:00")
    near.save(OUTPUT / "exif_near_plot.jpg", exif=near.info["exif"])
    far = add_exif(base_image(), 21.180000, 79.120000, "2026:11:21 16:30:00")
    far.save(OUTPUT / "exif_3km_away.jpg", exif=far.info["exif"])
    before = add_exif(base_image(), 21.145800, 79.088200, "2026:11:20 10:00:00")
    before.save(OUTPUT / "exif_before_event.jpg", exif=before.info["exif"])
    base_image().save(OUTPUT / "no_exif.png")
    base_image().save(OUTPUT / "sample.webp", format="WEBP")
    (OUTPUT / "corrupt.jpg").write_bytes(b"not a jpeg")
    (OUTPUT / "non_image.jpg").write_bytes(b"<html>not an image</html>")
    sharp.save(OUTPUT / "duplicate_a.jpg")
    sharp.save(OUTPUT / "duplicate_b.jpg")

    bomb = Image.new("RGB", (8000, 7500), (120, 130, 80))
    bomb.save(OUTPUT / "bomb_60mp.jpg", quality=60)
    print(f"Generated synthetic fixtures in {OUTPUT}")


if __name__ == "__main__":
    main()
