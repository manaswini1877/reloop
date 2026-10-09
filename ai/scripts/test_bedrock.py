#!/usr/bin/env python3
"""
ReLoop – Test script for Bedrock vision analysis.

Usage:
    python ai/scripts/test_bedrock.py ai/test_photos/swollen_battery.jpg
    python ai/scripts/test_bedrock.py --all
"""

import sys
import os
import io
import json
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# UTF-8 stdout/stderr on Windows so Telugu text renders correctly
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths (relative to this script, works from any working directory)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
SYSTEM_PROMPT_PATH = AI_DIR / "prompts" / "analyze_system.txt"
SCHEMA_PATH = AI_DIR / "schema" / "analysis.schema.json"
TEST_PHOTOS_DIR = AI_DIR / "test_photos"
ENV_PATH = AI_DIR / ".env"

IMAGE_FORMAT_MAP = {".jpg": "jpeg", ".jpeg": "jpeg", ".jfif": "jpeg", ".png": "png"}

# ---------------------------------------------------------------------------
# Load .env (before any env-var reads)
# ---------------------------------------------------------------------------
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ENV_PATH)

import boto3  # noqa: E402
import jsonschema  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_bedrock_client():
    """Create a bedrock-runtime client using the named AWS profile (or default chain)."""
    profile = os.environ.get("AWS_PROFILE")
    region = os.environ.get("AWS_REGION", "us-east-1")
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("bedrock-runtime")


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if the model accidentally added them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening fence line
        lines = lines[1:]
        # Drop closing fence line
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def image_format(path: Path) -> str:
    fmt = IMAGE_FORMAT_MAP.get(path.suffix.lower())
    if fmt is None:
        raise ValueError(f"Unsupported image extension '{path.suffix}'. Use .jpg, .jpeg, or .png.")
    return fmt


def call_bedrock(client, model_id: str, system_prompt: str, image_path: Path) -> str:
    """Send an image to Bedrock via the Converse API and return the raw text response."""
    img_bytes = image_path.read_bytes()
    fmt = image_format(image_path)

    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": fmt,
                            "source": {"bytes": img_bytes},
                        }
                    },
                    {"text": "Analyze this item."},
                ],
            }
        ],
        system=[{"text": system_prompt}],
        inferenceConfig={"temperature": 0.0, "maxTokens": 1000},
    )

    return response["output"]["message"]["content"][0]["text"]


def parse_and_validate(raw_text: str, schema: dict):
    """
    Parse JSON from model output, validate against schema.
    Returns (parsed_dict, is_valid, error_message).
    """
    cleaned = strip_markdown_fences(raw_text)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, False, f"JSON parse error: {exc}"

    try:
        jsonschema.validate(instance=result, schema=schema)
        return result, True, None
    except jsonschema.ValidationError as exc:
        return result, False, exc.message


# ---------------------------------------------------------------------------
# Single-image mode
# ---------------------------------------------------------------------------

def run_single(client, model_id: str, system_prompt: str, schema: dict, image_path: str):
    path = Path(image_path)
    if not path.is_file():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = call_bedrock(client, model_id, system_prompt, path)
    except Exception as exc:
        print(f"ERROR: Bedrock call failed: {exc}", file=sys.stderr)
        sys.exit(1)

    result, valid, err = parse_and_validate(raw, schema)
    if result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Raw model output:\n{raw}", file=sys.stderr)

    if valid:
        print("\nVALID")
    else:
        print(f"\nINVALID: {err}")


# ---------------------------------------------------------------------------
# Batch mode (--all)
# ---------------------------------------------------------------------------

def run_all(client, model_id: str, system_prompt: str, schema: dict):
    if not TEST_PHOTOS_DIR.is_dir():
        print(f"ERROR: Directory not found: {TEST_PHOTOS_DIR}", file=sys.stderr)
        sys.exit(1)

    images = sorted(
        p for p in TEST_PHOTOS_DIR.iterdir()
        if p.suffix.lower() in IMAGE_FORMAT_MAP
    )

    if not images:
        print(f"No images found in {TEST_PHOTOS_DIR}", file=sys.stderr)
        sys.exit(1)

    # Table header
    header = f"{'Filename':<35} {'Item':<20} {'Route':<10} {'Confidence':<12} {'Valid?':<8}"
    print(header)
    print("-" * len(header))

    for img_path in images:
        try:
            raw = call_bedrock(client, model_id, system_prompt, img_path)
            result, valid, err = parse_and_validate(raw, schema)

            item = result.get("item", "???") if result else "???"
            route = result.get("route", "???") if result else "???"
            conf = result.get("confidence", "???") if result else "???"
            valid_str = "YES" if valid else f"NO: {err}"

            print(f"{img_path.name:<35} {item:<20} {route:<10} {str(conf):<12} {valid_str}")

        except Exception as exc:
            print(f"{img_path.name:<35} {'ERROR':<20} {'---':<10} {'---':<12} {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ReLoop – Test Bedrock e-waste analysis")
    parser.add_argument("image", nargs="?", help="Path to an image file (.jpg/.jpeg/.png)")
    parser.add_argument("--all", action="store_true", help="Analyze every image in ai/test_photos/")
    args = parser.parse_args()

    if not args.all and not args.image:
        parser.error("Provide an image path or use --all")

    # ---- Check env vars ----
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    if not model_id or model_id == "<set-me>":
        print(
            "ERROR: BEDROCK_MODEL_ID is not set (or still '<set-me>').\n"
            "       Set it in ai/.env or as an environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ---- Set up clients and resources ----
    try:
        client = get_bedrock_client()
        system_prompt = load_system_prompt()
        schema = load_schema()
    except Exception as exc:
        print(f"ERROR: Setup failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # ---- Run ----
    if args.all:
        run_all(client, model_id, system_prompt, schema)
    else:
        run_single(client, model_id, system_prompt, schema, args.image)


if __name__ == "__main__":
    main()
