"""
analyze/pipeline.py
-------------------
Core analysis pipeline decoupled from AWS infrastructure.
Performs the Bedrock converse call, handles safety fallback for possible battery
items, and uses demo_cache for fallback during failures.
Does NOT import boto3 or read environment variables.
"""

import hashlib
import logging
from typing import Any

from logic import (
    apply_safety_rules,
    build_safe_hazard,
    extract_json,
    looks_like_battery,
    validate_and_normalize,
)

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Raised when analysis cannot be performed and safety fallback does not apply."""
    pass


def _lookup_cache(demo_cache: dict[str, Any] | None, image_hash: str) -> dict[str, Any] | None:
    """Check demo_cache for a pre-computed result, validated and normalized."""
    if not demo_cache or image_hash not in demo_cache:
        return None
    raw_cached = demo_cache[image_hash]
    validated = validate_and_normalize(raw_cached)
    return apply_safety_rules(validated)


def run_analysis(
    bedrock_client: Any,
    model_id: str,
    system_prompt: str,
    image_bytes: bytes,
    image_format: str,
    demo_cache: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    """
    Run Bedrock converse analysis on the image.

    Returns:
        (analysis_dict, source)
        where source is one of "model", "cache", "safety_fallback".

    Raises:
        AnalysisError when the analysis cannot be completed and no fallback applies.
    """
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    system_param = [{"text": system_prompt}] if system_prompt else []

    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": image_format,
                                "source": {
                                    "bytes": image_bytes,
                                },
                            }
                        },
                        {
                            "text": "Analyze this item.",
                        },
                    ],
                }
            ],
            system=system_param,
            inferenceConfig={
                "maxTokens": 600,
                "temperature": 0.0,
            },
        )
    except Exception as exc:
        logger.warning("Bedrock invocation failed: %s. Checking demo cache...", exc)
        cached_result = _lookup_cache(demo_cache, image_hash)
        if cached_result is not None:
            logger.info("Found matching entry in demo cache for hash %s", image_hash[:12])
            return cached_result, "cache"
        raise AnalysisError(f"Bedrock call failed: {exc}") from exc

    # Extract text from Converse response
    output_msg = response.get("output", {}).get("message", {})
    content_blocks = output_msg.get("content", [])
    raw_text = "".join(b.get("text", "") for b in content_blocks if isinstance(b, dict) and "text" in b)

    # Attempt JSON extraction and validation
    try:
        raw_json = extract_json(raw_text)
        validated = validate_and_normalize(raw_json)
        result = apply_safety_rules(validated)
        return result, "model"
    except (ValueError, Exception) as exc:
        logger.warning("Failed to parse/validate model output: %s", exc)

        # Safety Fallback: if raw text suggests a battery is present, route to hazard
        if looks_like_battery(raw_text):
            logger.info("Raw model text indicates potential battery. Triggering safe hazard fallback.")
            return build_safe_hazard(), "safety_fallback"

        # Check demo cache if available
        cached_result = _lookup_cache(demo_cache, image_hash)
        if cached_result is not None:
            logger.info("Model output was invalid, but found matching entry in demo cache for hash %s", image_hash[:12])
            return cached_result, "cache"

        # Neither safety fallback nor cache hit
        raise AnalysisError(f"Model output invalid and no safe fallback applies: {exc}") from exc
