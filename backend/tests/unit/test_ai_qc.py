import pytest

from app.services.ai_qc import apply_ai_signals, parse_ai_result


def test_parse_ai_result_sanitizes_unknown_values():
    raw = """{
      "is_crop_or_field_photo": true,
      "crop_guess": "chickpea",
      "crop_guess_confidence": "unknown",
      "shot_type_guess": "laser_scan",
      "visible_damage_present": true,
      "damage_notes": "Broken stems",
      "image_issues": ["blurry", "unknown_issue", "blurry"],
      "description": "A field photo",
      "retake_suggestions": ["Hold steady", "bad tip", "third tip", "fourth tip"]
    }"""

    result = parse_ai_result(raw)

    assert result["crop_guess_confidence"] == "low"
    assert result["shot_type_guess"] == "other"
    assert result["image_issues"] == ["blurry"]
    assert len(result["retake_suggestions"]) == 3


def test_parse_ai_result_rejects_malformed_json():
    with pytest.raises(ValueError):
        parse_ai_result("<script>alert(1)</script>")


def test_ai_signals_warn_but_never_fail():
    checks = apply_ai_signals(
        [{"code": "BLUR", "status": "pass", "value": 150, "message": "Sharp"}],
        {
            "is_crop_or_field_photo": True,
            "crop_guess": "wheat",
            "crop_guess_confidence": "high",
            "shot_type_guess": "close_up",
            "image_issues": ["screenshot_or_photo_of_screen", "faces_visible"],
        },
        "chickpea",
        "wide",
    )

    assert any(check["code"] == "AI_CROP_MISMATCH" for check in checks)
    assert any(check["code"] == "AI_SCREEN_PHOTO" for check in checks)
    assert not any(check["status"] == "fail" for check in checks)
