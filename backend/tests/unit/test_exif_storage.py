from pathlib import Path
from types import SimpleNamespace

from app.services import storage
from app.services.exif import extract_exif

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "images"


def test_extract_exif_from_synthetic_near_plot_fixture():
    path = FIXTURES / "exif_near_plot.jpg"
    if not path.exists():
        return
    result = extract_exif(path.read_bytes())
    assert result["has_exif"] is True
    assert result["taken_at"] is not None
    assert result["gps_lat"] is not None
    assert result["gps_lng"] is not None


def test_extract_exif_fails_soft_for_no_exif_png():
    path = FIXTURES / "no_exif.png"
    if not path.exists():
        return
    result = extract_exif(path.read_bytes())
    assert result["has_exif"] is False


class FakeBucket:
    def __init__(self):
        self.calls = []

    def upload(self, **kwargs):
        self.calls.append(("upload", kwargs))

    def create_signed_url(self, path, ttl):
        self.calls.append(("signed", path, ttl))
        return {"signedURL": f"https://example.test/{path}?ttl={ttl}"}

    def remove(self, paths):
        self.calls.append(("remove", paths))


def test_storage_helpers_generate_paths_and_signed_urls(monkeypatch):
    bucket = FakeBucket()
    fake = SimpleNamespace(storage=SimpleNamespace(from_=lambda _name: bucket))
    monkeypatch.setattr(storage, "get_supabase", lambda: fake)
    monkeypatch.setattr(
        storage,
        "get_settings",
        lambda: SimpleNamespace(
            supabase_storage_bucket="evidence",
            signed_url_ttl_seconds=600,
        ),
    )

    paths = storage.get_storage_paths("user", "incident", "photo", "png")
    assert paths["original"].startswith("user/incident/photos/photo/")
    storage.upload_photo_files(paths, b"original", b"display", b"thumb", "image/png")
    assert len(bucket.calls) == 3
    url = storage.create_signed_urls(paths)["display"]
    assert "example.test" in url
    storage.delete_photo_files(paths)
    assert bucket.calls[-1][0] == "remove"
