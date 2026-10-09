# -*- coding: utf-8 -*-
"""
ReLoop – Offline Logic Tests (No AWS required)
Tests validation, routing rules, steps formatting, and error handling.
"""

import sys
import io
import json
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure 'ai' directory is on sys.path
AI_DIR = Path(__file__).resolve().parent
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from analyzer import validate, apply_routing, build_result, AnalyzerError
from steps import STEPS


def run_tests():
    total = 0
    passed = 0

    def check(name, condition):
        nonlocal total, passed
        total += 1
        if condition:
            passed += 1
            print(f"PASS: {name}")
        else:
            print(f"FAIL: {name}")

    print("=== 1. Testing ai/examples/*.json routing ===")
    examples_dir = AI_DIR / "examples"
    expected_routes = {
        "hazard.json": "hazard",
        "repair.json": "repair",
        "reuse.json": "reuse",
        "recycle.json": "recycle",
    }

    for filename, expected_route in expected_routes.items():
        file_path = examples_dir / filename
        data = json.loads(file_path.read_text(encoding="utf-8"))
        result = build_result(data)
        check(
            f"Example '{filename}' routes to '{expected_route}'",
            result["route"] == expected_route
        )

    print("\n=== 2. Testing rule: low confidence (< 0.6) with battery -> hazard ===")
    low_conf_battery_data = {
        "item": "fitness band",
        "condition": "worn",
        "battery_risk": "low",
        "swollen_battery": False,
        "repairable": False,
        "still_usable": True,
        "confidence": 0.4,
        "reason": "Blurry image of fitness band with battery.",
    }
    res_low_conf = build_result(low_conf_battery_data)
    check(
        "battery_risk 'low' with confidence 0.4 routes to 'hazard'",
        res_low_conf["route"] == "hazard"
    )

    print("\n=== 3. Testing invalid confidence (string 'high') -> AnalyzerError ===")
    invalid_conf_data = {
        "item": "mouse",
        "condition": "good",
        "battery_risk": "none",
        "swollen_battery": False,
        "repairable": False,
        "still_usable": True,
        "confidence": "high",
        "reason": "Test mouse.",
    }
    threw = False
    try:
        validate(invalid_conf_data)
    except AnalyzerError as exc:
        threw = True
        print(f"      Caught expected AnalyzerError: {exc}")
    check("confidence 'high' (string) raises AnalyzerError", threw)

    print("\n=== 4. Testing missing field -> AnalyzerError ===")
    missing_field_data = {
        "item": "mouse",
        "condition": "good",
        # battery_risk missing
        "swollen_battery": False,
        "repairable": False,
        "still_usable": True,
        "confidence": 0.9,
        "reason": "Test mouse.",
    }
    threw = False
    try:
        validate(missing_field_data)
    except AnalyzerError as exc:
        threw = True
        print(f"      Caught expected AnalyzerError: {exc}")
    check("Missing required field raises AnalyzerError", threw)

    print("\n=== 5. Testing swollen_battery 'true' (string) -> AnalyzerError ===")
    string_bool_data = {
        "item": "phone",
        "condition": "damaged",
        "battery_risk": "high",
        "swollen_battery": "true",  # string instead of real bool
        "repairable": False,
        "still_usable": False,
        "confidence": 0.8,
        "reason": "Test phone.",
    }
    threw = False
    try:
        validate(string_bool_data)
    except AnalyzerError as exc:
        threw = True
        print(f"      Caught expected AnalyzerError: {exc}")
    check("swollen_battery 'true' (string) raises AnalyzerError", threw)

    print("\n=== 6. Verifying Telugu text in steps.py ===")
    for route, step_dict in STEPS.items():
        print(f"\nRoute: [{route.upper()}]")
        print("  English steps:")
        for idx, s in enumerate(step_dict["en"], 1):
            print(f"    {idx}. {s}")
        print("  Telugu steps:")
        for idx, s in enumerate(step_dict["te"], 1):
            print(f"    {idx}. {s}")
        check(f"Route '{route}' has 3 English and 3 Telugu steps", len(step_dict["en"]) == 3 and len(step_dict["te"]) == 3)

    print(f"\n==========================================")
    print(f"Summary: {passed}/{total} tests passed.")
    if passed == total:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
