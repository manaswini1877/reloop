# -*- coding: utf-8 -*-
"""
ReLoop – AI Analyzer Module
Validates raw model analysis, calculates safe routing, and attaches localized steps.
"""

import os
import sys
import json
from pathlib import Path

try:
    from ai.steps import STEPS
except ImportError:
    from steps import STEPS


class AnalyzerError(Exception):
    """Custom exception raised when validation, parsing, or Bedrock invocation fails."""
    pass


REQUIRED_FIELDS = [
    "item",
    "condition",
    "battery_risk",
    "swollen_battery",
    "repairable",
    "still_usable",
    "confidence",
    "reason",
]

ALLOWED_CONDITIONS = {"good", "worn", "damaged"}
ALLOWED_BATTERY_RISKS = {"none", "low", "medium", "high"}


def validate(data: dict) -> dict:
    """
    Validate that data contains all 8 required fields with correct types and enum values.
    Raises AnalyzerError with a clear message naming the offending field on failure.
    """
    if not isinstance(data, dict):
        raise AnalyzerError("Input data must be a dictionary")

    # Check for presence of all required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            raise AnalyzerError(f"Missing required field: '{field}'")

    # Validate 'item'
    if not isinstance(data["item"], str) or not data["item"].strip():
        raise AnalyzerError("Invalid field 'item': must be a non-empty string")

    # Validate 'condition' enum
    if data["condition"] not in ALLOWED_CONDITIONS:
        raise AnalyzerError(
            f"Invalid field 'condition': got '{data['condition']}', expected one of {sorted(ALLOWED_CONDITIONS)}"
        )

    # Validate 'battery_risk' enum
    if data["battery_risk"] not in ALLOWED_BATTERY_RISKS:
        raise AnalyzerError(
            f"Invalid field 'battery_risk': got '{data['battery_risk']}', expected one of {sorted(ALLOWED_BATTERY_RISKS)}"
        )

    # Validate boolean fields (strictly bool, not string or int)
    for bool_field in ["swollen_battery", "repairable", "still_usable"]:
        if type(data[bool_field]) is not bool:
            raise AnalyzerError(
                f"Invalid field '{bool_field}': must be a boolean (True/False), got {type(data[bool_field]).__name__}"
            )

    # Validate 'confidence' (float or int between 0 and 1, not bool)
    conf = data["confidence"]
    if type(conf) not in (int, float) or isinstance(conf, bool) or not (0.0 <= float(conf) <= 1.0):
        raise AnalyzerError(
            f"Invalid field 'confidence': must be a number between 0 and 1, got {conf!r}"
        )

    # Validate 'reason'
    if not isinstance(data["reason"], str) or not data["reason"].strip():
        raise AnalyzerError("Invalid field 'reason': must be a non-empty string")

    return data


def apply_routing(data: dict) -> str:
    """
    Determine the disposal route based on priority rules:
    1. swollen_battery is true OR battery_risk is 'high' -> 'hazard'
    2. battery_risk is not 'none' AND confidence < 0.6 -> 'hazard' (safety default)
    3. repairable is true -> 'repair'
    4. still_usable is true AND condition is good or worn -> 'reuse'
    5. otherwise -> 'recycle'
    """
    # Rule 1: swollen_battery is true OR battery_risk is 'high' -> 'hazard'
    if data.get("swollen_battery") is True or data.get("battery_risk") == "high":
        return "hazard"

    # Rule 2: battery_risk is not 'none' AND confidence < 0.6 -> 'hazard' (safety default)
    if data.get("battery_risk") != "none" and data.get("confidence", 0) < 0.6:
        return "hazard"

    # Rule 3: repairable is true -> 'repair'
    if data.get("repairable") is True:
        return "repair"

    # Rule 4: still_usable is true AND condition is good or worn -> 'reuse'
    if data.get("still_usable") is True and data.get("condition") in ("good", "worn"):
        return "reuse"

    # Rule 5: otherwise -> 'recycle'
    return "recycle"


def build_result(data: dict) -> dict:
    """
    Validate raw model fields, apply routing logic, and attach localized handling steps.
    """
    validated = validate(data)
    route = apply_routing(validated)

    if route not in STEPS:
        raise AnalyzerError(f"Route '{route}' not found in STEPS configuration")

    result = dict(validated)
    result["route"] = route
    result["safe_steps_en"] = STEPS[route]["en"]
    result["safe_steps_te"] = STEPS[route]["te"]
    return result


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def analyze_image(image_bytes: bytes, image_format: str) -> dict:
    """
    Calls Bedrock converse API with image and prompt, parses and validates result.
    Raises AnalyzerError on any AWS, JSON, or validation failure. Never crashes with raw traceback.
    """
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    if not model_id:
        raise AnalyzerError("BEDROCK_MODEL_ID environment variable is not set")

    region = os.environ.get("AWS_REGION", "us-east-1")
    profile = os.environ.get("AWS_PROFILE")

    # Load system prompt
    prompt_path = Path(__file__).resolve().parent / "prompt.txt"
    if not prompt_path.is_file():
        raise AnalyzerError(f"System prompt file not found at: {prompt_path}")

    try:
        system_prompt = prompt_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        raise AnalyzerError(f"Failed to read prompt file: {exc}")

    # Initialize boto3 Bedrock client
    try:
        import boto3
        if profile:
            session = boto3.Session(profile_name=profile, region_name=region)
        else:
            session = boto3.Session(region_name=region)
        client = session.client("bedrock-runtime")
    except Exception as exc:
        raise AnalyzerError(f"Failed to initialize AWS Bedrock client: {exc}")

    # Normalize image format string
    norm_format = image_format.lower().lstrip(".")
    if norm_format in ("jpg", "jpeg", "jfif"):
        bedrock_format = "jpeg"
    elif norm_format == "png":
        bedrock_format = "png"
    else:
        bedrock_format = norm_format

    try:
        response = client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": bedrock_format,
                                "source": {"bytes": image_bytes},
                            }
                        },
                        {"text": "Analyze this item."},
                    ],
                }
            ],
            system=[{"text": system_prompt}],
            inferenceConfig={"temperature": 0.0, "maxTokens": 1000},
        )
        raw_text = response["output"]["message"]["content"][0]["text"]
    except Exception as exc:
        raise AnalyzerError(f"Bedrock invocation failed: {exc}")

    cleaned = _strip_markdown_fences(raw_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AnalyzerError(f"Failed to parse model output as JSON: {exc}")

    return build_result(parsed)
