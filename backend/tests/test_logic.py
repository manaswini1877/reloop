"""
tests/test_logic.py
-------------------
Unit tests for logic.py using standard Python assertions (no third-party test runners needed).
Run with:
    py -3.12 backend\tests\test_logic.py
"""

import os
import sys

# Ensure functions/analyze is on the import path
ANALYZE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "functions", "analyze")
)
if ANALYZE_DIR not in sys.path:
    sys.path.insert(0, ANALYZE_DIR)

from logic import (
    apply_safety_rules,
    build_safe_hazard,
    detect_image_type,
    extract_json,
    looks_like_battery,
    mock_result,
    validate_and_normalize,
)


def sample_valid_dict() -> dict:
    return {
        "item": "power bank",
        "condition": "damaged",
        "battery_risk": "high",
        "swollen_battery": True,
        "route": "hazard",
        "confidence": 0.85,
        "reason": "Battery is bulging.",
        "safe_steps_en": ["Step 1", "Step 2", "Step 3"],
        "safe_steps_te": ["Step 1 in te", "Step 2 in te", "Step 3 in te"],
    }


# ── Test extract_json ─────────────────────────────────────────────────────────

def test_extract_json():
    print("Testing extract_json...")

    # 1. Plain clean JSON
    res = extract_json('{"key": "value"}')
    assert res == {"key": "value"}, f"Failed plain JSON: {res}"

    # 2. Code-fenced JSON (```json ... ```)
    fenced = """```json
    {
        "item": "phone",
        "condition": "good"
    }
    ```"""
    res = extract_json(fenced)
    assert res["item"] == "phone"
    assert res["condition"] == "good"

    # 3. Code fence without language identifier (``` ... ```)
    fenced_no_lang = """```
    {"route": "recycle"}
    ```"""
    res = extract_json(fenced_no_lang)
    assert res["route"] == "recycle"

    # 4. JSON with extra conversational text before and after
    with_chatter = (
        "Here is the item analysis:\n"
        '{"item": "keyboard", "route": "recycle", "confidence": 0.95}\n'
        "I hope this helps you categorize the e-waste."
    )
    res = extract_json(with_chatter)
    assert res["item"] == "keyboard"
    assert res["route"] == "recycle"
    assert res["confidence"] == 0.95

    # 5. Invalid text: no JSON braces
    try:
        extract_json("There is no JSON in this response.")
        assert False, "Should have raised ValueError for no JSON"
    except ValueError:
        pass

    # 6. Invalid text: broken JSON syntax
    try:
        extract_json("{item: broken, no quotes}")
        assert False, "Should have raised ValueError for broken JSON"
    except ValueError:
        pass

    print("  [OK] extract_json passed all tests")


# ── Test validate_and_normalize ───────────────────────────────────────────────

def test_validate_and_normalize():
    print("Testing validate_and_normalize...")

    # 1. Valid input
    valid_data = sample_valid_dict()
    normalized = validate_and_normalize(valid_data)
    assert normalized["item"] == "power bank"
    assert normalized["confidence"] == 0.85
    assert isinstance(normalized["confidence"], float)
    assert normalized["swollen_battery"] is True

    # 2. Missing required field
    missing_data = sample_valid_dict()
    del missing_data["route"]
    try:
        validate_and_normalize(missing_data)
        assert False, "Should have raised ValueError for missing 'route'"
    except ValueError as exc:
        assert "Missing required field: 'route'" in str(exc)

    # 3. Bad enum: condition
    bad_cond = sample_valid_dict()
    bad_cond["condition"] = "broken"  # allowed: good|worn|damaged
    try:
        validate_and_normalize(bad_cond)
        assert False, "Should have raised ValueError for invalid condition"
    except ValueError as exc:
        assert "'condition' must be one of" in str(exc)

    # 4. Bad enum: battery_risk
    bad_risk = sample_valid_dict()
    bad_risk["battery_risk"] = "critical"  # allowed: none|low|medium|high
    try:
        validate_and_normalize(bad_risk)
        assert False, "Should have raised ValueError for invalid battery_risk"
    except ValueError as exc:
        assert "'battery_risk' must be one of" in str(exc)

    # 5. Bad enum: route
    bad_route = sample_valid_dict()
    bad_route["route"] = "landfill"  # allowed: hazard|repair|recycle
    try:
        validate_and_normalize(bad_route)
        assert False, "Should have raised ValueError for invalid route"
    except ValueError as exc:
        assert "'route' must be one of" in str(exc)

    # 6. Wrong type: swollen_battery as string instead of bool
    bad_bool = sample_valid_dict()
    bad_bool["swollen_battery"] = "true"  # must be bool
    try:
        validate_and_normalize(bad_bool)
        assert False, "Should have raised ValueError for string swollen_battery"
    except ValueError as exc:
        assert "'swollen_battery' must be a boolean" in str(exc)

    # 7. Wrong type: confidence as string
    bad_conf = sample_valid_dict()
    bad_conf["confidence"] = "0.85"
    try:
        validate_and_normalize(bad_conf)
        assert False, "Should have raised ValueError for string confidence"
    except ValueError as exc:
        assert "'confidence' must be a number" in str(exc)

    # 8. Confidence clamped to 0..1
    over_conf = sample_valid_dict()
    over_conf["confidence"] = 1.4
    norm = validate_and_normalize(over_conf)
    assert norm["confidence"] == 1.0

    # 9. Step list validation: empty list
    empty_steps = sample_valid_dict()
    empty_steps["safe_steps_en"] = []
    try:
        validate_and_normalize(empty_steps)
        assert False, "Should have raised ValueError for empty step list"
    except ValueError as exc:
        assert "'safe_steps_en' must be a non-empty list" in str(exc)

    print("  [OK] validate_and_normalize passed all tests")


# ── Test apply_safety_rules ───────────────────────────────────────────────────

def test_apply_safety_rules():
    print("Testing apply_safety_rules...")

    # 1. Swollen battery forces hazard and high battery_risk regardless of route
    item1 = {
        "item": "power bank",
        "condition": "worn",
        "battery_risk": "low",
        "swollen_battery": True,
        "route": "repair",  # Model mistakenly said repair
        "confidence": 0.9,
        "reason": "Battery shows slight bulging.",
        "safe_steps_en": ["Step 1"],
        "safe_steps_te": ["Step 1 in te"],
    }
    res1 = apply_safety_rules(item1)
    assert res1["route"] == "hazard", f"Expected hazard, got {res1['route']}"
    assert res1["battery_risk"] == "high", f"Expected high, got {res1['battery_risk']}"

    # 2. Low confidence (< 0.6) with battery present (battery_risk != 'none') forces hazard
    item2 = {
        "item": "unidentified circuit with battery",
        "condition": "worn",
        "battery_risk": "low",
        "swollen_battery": False,
        "route": "recycle",  # Model said recycle
        "confidence": 0.45,  # Confidence < 0.6
        "reason": "Blurry image with battery cylinder visible.",
        "safe_steps_en": ["Step A"],
        "safe_steps_te": ["Step A in te"],
    }
    res2 = apply_safety_rules(item2)
    assert res2["route"] == "hazard", f"Expected hazard for low conf battery, got {res2['route']}"

    # 3. Good keyboard with no battery (battery_risk == 'none') stays recycle
    item3 = {
        "item": "keyboard",
        "condition": "good",
        "battery_risk": "none",
        "swollen_battery": False,
        "route": "recycle",
        "confidence": 0.95,
        "reason": "Standard USB keyboard with no battery.",
        "safe_steps_en": ["Unplug", "Recycle at bin"],
        "safe_steps_te": ["Step in te"],
    }
    res3 = apply_safety_rules(item3)
    assert res3["route"] == "recycle", f"Expected recycle, got {res3['route']}"
    assert res3["battery_risk"] == "none"

    # 4. Low confidence with NO battery (battery_risk == 'none') stays its original route
    item4 = {
        "item": "cable",
        "condition": "worn",
        "battery_risk": "none",
        "swollen_battery": False,
        "route": "recycle",
        "confidence": 0.40,
        "reason": "Blurry cable.",
        "safe_steps_en": ["Recycle"],
        "safe_steps_te": ["Step in te"],
    }
    res4 = apply_safety_rules(item4)
    assert res4["route"] == "recycle", f"Non-battery low confidence item should stay recycle, got {res4['route']}"

    print("  [OK] apply_safety_rules passed all tests")


# ── Test looks_like_battery ───────────────────────────────────────────────────

def test_looks_like_battery():
    print("Testing looks_like_battery...")

    # True cases
    assert looks_like_battery("This device contains a lithium battery.") is True
    assert looks_like_battery("Found swollen cells inside.") is True
    assert looks_like_battery("The casing has a distinct bulg.") is True
    assert looks_like_battery("Disassembled power bank.") is True
    assert looks_like_battery("Damaged mobile phone.") is True
    assert looks_like_battery("Old earbuds case with li-ion power.") is True
    assert looks_like_battery("Disposable vape device.") is True

    # False cases
    assert looks_like_battery("A plastic monitor stand.") is False
    assert looks_like_battery("Wooden desk organizer.") is False
    assert looks_like_battery("USB cable with cracked insulation.") is False
    assert looks_like_battery("") is False

    print("  [OK] looks_like_battery passed all tests")


# ── Test build_safe_hazard ────────────────────────────────────────────────────

def test_build_safe_hazard():
    print("Testing build_safe_hazard...")
    hazard = build_safe_hazard()

    # Validate against contract requirements
    validated = validate_and_normalize(hazard)
    assert validated["route"] == "hazard"
    assert validated["battery_risk"] == "medium"
    assert validated["swollen_battery"] is False
    assert validated["confidence"] == 0.3
    assert len(validated["safe_steps_en"]) >= 1
    assert len(validated["safe_steps_te"]) >= 1

    print("  [OK] build_safe_hazard passed all tests")


# ── Test detect_image_type ────────────────────────────────────────────────────

def test_detect_image_type():
    print("Testing detect_image_type...")

    # 1. JPEG: starts with FF D8 FF
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
    assert detect_image_type(jpeg_bytes) == "jpeg"

    # 2. PNG: starts with 89 50 4E 47
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    assert detect_image_type(png_bytes) == "png"

    # 3. WEBP: RIFF....WEBP
    webp_bytes = b"RIFF\x24\x00\x00\x00WEBPVP8 "
    assert detect_image_type(webp_bytes) == "webp"

    # 4. Invalid / fake data
    assert detect_image_type(b"GIF89a...") is None
    assert detect_image_type(b"%PDF-1.4...") is None
    assert detect_image_type(b"plain text data") is None
    assert detect_image_type(b"") is None
    assert detect_image_type(None) is None

    print("  [OK] detect_image_type passed all tests")


# ── Test mock_result ──────────────────────────────────────────────────────────

def test_mock_result():
    print("Testing mock_result...")
    keys = [
        "uploads/seed-1.jpg",
        "uploads/seed-2.jpg",
        "uploads/seed-3.jpg",
        "uploads/test-image.png",
    ]
    for k in keys:
        res = mock_result(k)
        assert res["route"] in ("hazard", "repair", "recycle")
        assert res["condition"] in ("good", "worn", "damaged")
        assert res["battery_risk"] in ("none", "low", "medium", "high")
        assert isinstance(res["swollen_battery"], bool)
        assert isinstance(res["confidence"], (int, float))
        assert len(res["safe_steps_en"]) >= 1
        assert len(res["safe_steps_te"]) >= 1

    print("  [OK] mock_result passed all tests")


# ── Run all tests ─────────────────────────────────────────────────────────────

def main():
    print("Running ReLoop analyze unit tests...\n")
    test_extract_json()
    test_validate_and_normalize()
    test_apply_safety_rules()
    test_looks_like_battery()
    test_build_safe_hazard()
    test_detect_image_type()
    test_mock_result()
    print("\nALL UNIT TESTS PASSED!")


if __name__ == "__main__":
    main()
