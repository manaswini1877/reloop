"""
tests/test_pipeline.py
---------------------
Unit tests for pipeline.py using fake Bedrock clients (no AWS calls or credentials needed).
Run with:
    py -3.12 backend\tests\test_pipeline.py
"""

import hashlib
import json
import os
import sys

# Ensure functions/analyze is on the import path
ANALYZE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "functions", "analyze")
)
if ANALYZE_DIR not in sys.path:
    sys.path.insert(0, ANALYZE_DIR)

from pipeline import (
    AnalysisError,
    run_analysis,
)


class FakeBedrockClient:
    """Mock Bedrock client implementing converse() without network calls."""

    def __init__(
        self,
        response_text: str | None = None,
        raise_exception: Exception | None = None,
    ):
        self.response_text = response_text
        self.raise_exception = raise_exception
        self.last_kwargs: dict = {}

    def converse(self, **kwargs):
        self.last_kwargs = kwargs
        if self.raise_exception:
            raise self.raise_exception
        return {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": self.response_text or ""}],
                }
            }
        }


def sample_analysis_dict() -> dict:
    return {
        "item": "smartphone",
        "condition": "damaged",
        "battery_risk": "low",
        "swollen_battery": False,
        "route": "repair",
        "confidence": 0.88,
        "reason": "Cracked screen.",
        "safe_steps_en": ["Step 1", "Step 2", "Step 3"],
        "safe_steps_te": ["Step 1 in te", "Step 2 in te", "Step 3 in te"],
    }


# ── Test Cases ────────────────────────────────────────────────────────────────

def test_valid_model_json():
    print("Testing valid model JSON -> source 'model'...")
    data = sample_analysis_dict()
    client = FakeBedrockClient(response_text=json.dumps(data))

    result, source = run_analysis(
        bedrock_client=client,
        model_id="test-model",
        system_prompt="Test prompt",
        image_bytes=b"dummy_bytes",
        image_format="jpeg",
        demo_cache={},
    )
    assert source == "model", f"Expected source 'model', got '{source}'"
    assert result["item"] == "smartphone"
    assert result["route"] == "repair"
    assert result["confidence"] == 0.88
    print("  [OK] Valid model response returned source 'model'")


def test_garbage_text_with_battery_keyword():
    print("Testing garbage text with battery keyword -> safety fallback...")
    garbage_with_battery = "I think there is a lithium battery inside, but I cannot format as JSON."
    client = FakeBedrockClient(response_text=garbage_with_battery)

    result, source = run_analysis(
        bedrock_client=client,
        model_id="test-model",
        system_prompt="Test prompt",
        image_bytes=b"dummy_bytes",
        image_format="jpeg",
        demo_cache={},
    )
    assert source == "safety_fallback", f"Expected 'safety_fallback', got '{source}'"
    assert result["route"] == "hazard"
    assert result["battery_risk"] == "medium"
    assert result["confidence"] == 0.3
    assert "Unidentified item" in result["item"]
    print("  [OK] Battery hint triggered safety_fallback")


def test_garbage_text_without_battery_raises_error():
    print("Testing garbage text without battery -> AnalysisError...")
    garbage_no_battery = "I am a helpful assistant and this is a plastic bottle."
    client = FakeBedrockClient(response_text=garbage_no_battery)

    try:
        run_analysis(
            bedrock_client=client,
            model_id="test-model",
            system_prompt="Test prompt",
            image_bytes=b"dummy_bytes",
            image_format="jpeg",
            demo_cache={},
        )
        assert False, "Should have raised AnalysisError"
    except AnalysisError:
        pass
    print("  [OK] Garbage without battery hint raised AnalysisError")


def test_client_exception_without_cache_raises_error():
    print("Testing Bedrock client exception without cache -> AnalysisError...")
    client = FakeBedrockClient(raise_exception=RuntimeError("ThrottlingException: Rate exceeded"))

    try:
        run_analysis(
            bedrock_client=client,
            model_id="test-model",
            system_prompt="Test prompt",
            image_bytes=b"dummy_bytes",
            image_format="jpeg",
            demo_cache={},
        )
        assert False, "Should have raised AnalysisError"
    except AnalysisError:
        pass
    print("  [OK] Exception without cache raised AnalysisError")


def test_client_exception_with_cache_hit():
    print("Testing Bedrock client exception with matching cache -> source 'cache'...")
    image_bytes = b"cached_demo_image_bytes"
    img_hash = hashlib.sha256(image_bytes).hexdigest()
    cached_item = sample_analysis_dict()
    demo_cache = {img_hash: cached_item}

    client = FakeBedrockClient(raise_exception=RuntimeError("ModelTimeout"))

    result, source = run_analysis(
        bedrock_client=client,
        model_id="test-model",
        system_prompt="Test prompt",
        image_bytes=image_bytes,
        image_format="jpeg",
        demo_cache=demo_cache,
    )
    assert source == "cache", f"Expected source 'cache', got '{source}'"
    assert result["item"] == "smartphone"
    assert result["route"] == "repair"
    print("  [OK] Exception with cache hit returned source 'cache'")


def test_safety_rules_low_confidence_battery():
    print("Testing model low confidence on battery -> forces hazard...")
    item = sample_analysis_dict()
    item["confidence"] = 0.45
    item["battery_risk"] = "low"
    item["route"] = "repair"  # Model says repair, but confidence < 0.6 with battery
    client = FakeBedrockClient(response_text=json.dumps(item))

    result, source = run_analysis(
        bedrock_client=client,
        model_id="test-model",
        system_prompt="Test prompt",
        image_bytes=b"dummy_bytes",
        image_format="jpeg",
    )
    assert source == "model"
    assert result["route"] == "hazard", f"Expected 'hazard' for low confidence battery, got '{result['route']}'"
    print("  [OK] Low confidence battery forced route='hazard'")


def test_safety_rules_swollen_battery():
    print("Testing swollen_battery -> forces hazard & high risk...")
    item = sample_analysis_dict()
    item["swollen_battery"] = True
    item["battery_risk"] = "low"
    item["route"] = "repair"
    client = FakeBedrockClient(response_text=json.dumps(item))

    result, source = run_analysis(
        bedrock_client=client,
        model_id="test-model",
        system_prompt="Test prompt",
        image_bytes=b"dummy_bytes",
        image_format="jpeg",
    )
    assert source == "model"
    assert result["route"] == "hazard"
    assert result["battery_risk"] == "high"
    print("  [OK] Swollen battery forced hazard and high risk")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Running ReLoop pipeline unit tests...\n")
    test_valid_model_json()
    test_garbage_text_with_battery_keyword()
    test_garbage_text_without_battery_raises_error()
    test_client_exception_without_cache_raises_error()
    test_client_exception_with_cache_hit()
    test_safety_rules_low_confidence_battery()
    test_safety_rules_swollen_battery()
    print("\nALL PIPELINE TESTS PASSED!")


if __name__ == "__main__":
    main()
