"""
analyze/logic.py
----------------
Pure functions with no AWS calls so they can be tested on a laptop.
Imported by app.py at runtime and by tests/test_logic.py locally.
"""

import hashlib
import json
import re
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_CONDITIONS   = {"good", "worn", "damaged"}
ALLOWED_BATTERY_RISK = {"none", "low", "medium", "high"}
ALLOWED_ROUTES       = {"hazard", "repair", "recycle"}

MAX_STEPS       = 8
MAX_STEP_CHARS  = 200

# Default hazard steps used when the model omits them.
DEFAULT_STEPS_EN = [
    "Keep away from heat",
    "Do not put in a bin",
    "Hand over to campus e-waste staff",
]
DEFAULT_STEPS_TE = [
    "వేడికి దూరంగా ఉంచండి",
    "చెత్తబుట్టలో వేయకండి",
    "క్యాంపస్ ఈ-వేస్ట్ సిబ్బందికి అప్పగించండి",
]


# ── extract_json ──────────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    """
    Strip code fences, then extract the substring from the first '{' to the
    last '}' and parse it as JSON.

    Raises ValueError if no JSON object is found or if parsing fails.
    """
    if not isinstance(text, str):
        raise ValueError("extract_json expects a string")

    # Remove code fences (``` or ```json … ```)
    text = re.sub(r"```[a-zA-Z]*", "", text)

    start = text.find("{")
    end   = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model output")

    json_str = text[start : end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error: {exc}") from exc


# ── validate_and_normalize ────────────────────────────────────────────────────

def _check_step_list(value: Any, field: str) -> list:
    """Validate that a field is a non-empty list of short strings."""
    if not isinstance(value, list) or len(value) == 0:
        raise ValueError(f"'{field}' must be a non-empty list of strings")
    if len(value) > MAX_STEPS:
        raise ValueError(f"'{field}' must have at most {MAX_STEPS} items")
    for i, step in enumerate(value):
        if not isinstance(step, str):
            raise ValueError(f"'{field}[{i}]' must be a string, got {type(step).__name__}")
        if len(step) > MAX_STEP_CHARS:
            raise ValueError(
                f"'{field}[{i}]' exceeds {MAX_STEP_CHARS} characters"
            )
    return value


def validate_and_normalize(raw: dict) -> dict:
    """
    Check that all 9 analysis fields exist with the right types and values.
    Returns a cleaned copy with confidence as float.
    Raises ValueError with a descriptive message on any problem.
    """
    required = [
        "item", "condition", "battery_risk", "swollen_battery",
        "route", "confidence", "reason", "safe_steps_en", "safe_steps_te",
    ]
    for field in required:
        if field not in raw:
            raise ValueError(f"Missing required field: '{field}'")

    # item
    if not isinstance(raw["item"], str) or not raw["item"].strip():
        raise ValueError("'item' must be a non-empty string")

    # condition
    condition = raw["condition"]
    if condition not in ALLOWED_CONDITIONS:
        raise ValueError(
            f"'condition' must be one of {sorted(ALLOWED_CONDITIONS)}, got '{condition}'"
        )

    # battery_risk
    battery_risk = raw["battery_risk"]
    if battery_risk not in ALLOWED_BATTERY_RISK:
        raise ValueError(
            f"'battery_risk' must be one of {sorted(ALLOWED_BATTERY_RISK)}, got '{battery_risk}'"
        )

    # swollen_battery – must be a real bool (not 0/1 int)
    if not isinstance(raw["swollen_battery"], bool):
        raise ValueError(
            f"'swollen_battery' must be a boolean, got {type(raw['swollen_battery']).__name__}"
        )

    # route
    route = raw["route"]
    if route not in ALLOWED_ROUTES:
        raise ValueError(
            f"'route' must be one of {sorted(ALLOWED_ROUTES)}, got '{route}'"
        )

    # confidence – accept int or float, clamp to [0, 1]
    raw_conf = raw["confidence"]
    if not isinstance(raw_conf, (int, float)):
        raise ValueError(
            f"'confidence' must be a number, got {type(raw_conf).__name__}"
        )
    confidence = float(max(0.0, min(1.0, raw_conf)))

    # reason
    if not isinstance(raw["reason"], str) or not raw["reason"].strip():
        raise ValueError("'reason' must be a non-empty string")

    # step lists
    safe_steps_en = _check_step_list(raw["safe_steps_en"], "safe_steps_en")
    safe_steps_te = _check_step_list(raw["safe_steps_te"], "safe_steps_te")

    return {
        "item":           raw["item"].strip(),
        "condition":      condition,
        "battery_risk":   battery_risk,
        "swollen_battery": raw["swollen_battery"],
        "route":          route,
        "confidence":     confidence,
        "reason":         raw["reason"].strip(),
        "safe_steps_en":  safe_steps_en,
        "safe_steps_te":  safe_steps_te,
    }


# ── apply_safety_rules ────────────────────────────────────────────────────────

def apply_safety_rules(result: dict) -> dict:
    """
    Enforce contract safety rules in code, regardless of what the model said.

    Rules (applied in this order):
      1. Swollen battery → route "hazard", battery_risk "high".
      2. confidence < 0.6 AND battery_risk != "none" → route "hazard".
      3. route == "hazard" AND step lists empty → fill with defaults.
    """
    out = dict(result)   # shallow copy — all values are immutable

    # Rule 1: swollen battery is always hazard / high risk
    if out.get("swollen_battery"):
        out["route"]        = "hazard"
        out["battery_risk"] = "high"

    # Rule 2: low-confidence battery item → hazard
    if out.get("confidence", 1.0) < 0.6 and out.get("battery_risk") != "none":
        out["route"] = "hazard"

    # Rule 3: hazard route must have step lists
    if out.get("route") == "hazard":
        if not out.get("safe_steps_en"):
            out["safe_steps_en"] = DEFAULT_STEPS_EN[:]
        if not out.get("safe_steps_te"):
            out["safe_steps_te"] = DEFAULT_STEPS_TE[:]

    return out


# ── mock_result ───────────────────────────────────────────────────────────────
# MOCK MODE IS FOR DEVELOPMENT / DEMO ONLY.
# Set USE_MOCK="false" and provide BEDROCK_MODEL_ID before going to production.

_MOCK_ANALYSES = [
    # 0 – hazard: swollen power bank
    {
        "item":           "power bank",
        "condition":      "damaged",
        "battery_risk":   "high",
        "swollen_battery": True,
        "route":          "hazard",
        "confidence":     0.92,
        "reason":         "Battery casing is visibly swollen and deformed.",
        "safe_steps_en":  DEFAULT_STEPS_EN[:],
        "safe_steps_te":  DEFAULT_STEPS_TE[:],
    },
    # 1 – repair: cracked phone
    {
        "item":           "smartphone",
        "condition":      "damaged",
        "battery_risk":   "low",
        "swollen_battery": False,
        "route":          "repair",
        "confidence":     0.87,
        "reason":         "Screen is cracked but the device is otherwise functional.",
        "safe_steps_en":  [
            "Back up your data before repair",
            "Take to an authorised repair centre",
            "Do not attempt self-repair",
        ],
        "safe_steps_te":  [
            "మరమ్మత్తు ముందు మీ డేటాను బ్యాకప్ చేయండి",
            "అధికారిక రిపేర్ సెంటర్‌కు తీసుకెళ్ళండి",
            "స్వయంగా మరమ్మత్తు చేయడానికి ప్రయత్నించకండి",
        ],
    },
    # 2 – recycle: old keyboard
    {
        "item":           "keyboard",
        "condition":      "worn",
        "battery_risk":   "none",
        "swollen_battery": False,
        "route":          "recycle",
        "confidence":     0.95,
        "reason":         "Keyboard is old and heavily worn; no battery present.",
        "safe_steps_en":  [
            "Do not put in household rubbish",
            "Drop off at the campus e-waste collection point",
            "Remove any USB dongles before recycling",
        ],
        "safe_steps_te":  [
            "గృహ చెత్తలో వేయకండి",
            "క్యాంపస్ ఈ-వేస్ట్ సేకరణ కేంద్రంలో వదలండి",
            "రీసైకిల్ చేయడానికి ముందు USB డోంగిల్స్ తొలగించండి",
        ],
    },
]


def mock_result(image_key: str) -> dict:
    """
    Return one of 3 realistic mock analyses chosen by a stable hash of image_key.
    Safety rules are pre-applied so the output already satisfies the contract.
    """
    bucket = int(hashlib.md5(image_key.encode()).hexdigest(), 16) % len(_MOCK_ANALYSES)
    return dict(_MOCK_ANALYSES[bucket])
