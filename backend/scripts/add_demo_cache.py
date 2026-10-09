"""
scripts/add_demo_cache.py
-------------------------
Populates or updates backend/functions/analyze/demo_cache.json with pre-computed
real model results indexed by the SHA-256 hash of the photo.

Usage (PowerShell):
    python backend/scripts/add_demo_cache.py --photo path/to/sample.jpg --result path/to/result.json

NOTE:
    This cache is for demo resilience only (e.g. during a recorded presentation
    or hackathon pitch in case Bedrock quotas or network issues arise).
    Entries must come from real model results (never fabricated).
    This must be explicitly disclosed in the project limitations list.
"""

import argparse
import hashlib
import json
import os
import sys

ANALYSIS_FIELDS = [
    "item",
    "condition",
    "battery_risk",
    "swollen_battery",
    "route",
    "confidence",
    "reason",
    "safe_steps_en",
    "safe_steps_te",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add an item analysis to the demo fallback cache.")
    parser.add_argument("--photo", required=True, help="Path to the image file")
    parser.add_argument("--result", required=True, help="Path to JSON file with the analysis result")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not os.path.exists(args.photo):
        print(f"ERROR: Photo not found at '{args.photo}'", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.result):
        print(f"ERROR: Result JSON not found at '{args.result}'", file=sys.stderr)
        sys.exit(1)

    # 1. Compute SHA-256 of the photo
    with open(args.photo, "rb") as f:
        photo_bytes = f.read()
    image_hash = hashlib.sha256(photo_bytes).hexdigest()
    print(f"Photo: {args.photo} ({len(photo_bytes)} bytes)")
    print(f"SHA-256: {image_hash}")

    # 2. Read and filter result JSON
    with open(args.result, "r", encoding="utf-8") as f:
        try:
            result_data = json.load(f)
        except json.JSONDecodeError as exc:
            print(f"ERROR: Invalid JSON in '{args.result}': {exc}", file=sys.stderr)
            sys.exit(1)

    # Extract only the 9 analysis fields
    cleaned_analysis = {}
    missing = []
    for field in ANALYSIS_FIELDS:
        if field in result_data:
            cleaned_analysis[field] = result_data[field]
        else:
            missing.append(field)

    if missing:
        print(f"ERROR: Result JSON is missing required fields: {missing}", file=sys.stderr)
        sys.exit(1)

    # 3. Load demo_cache.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.abspath(
        os.path.join(script_dir, "..", "functions", "analyze", "demo_cache.json")
    )

    demo_cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                demo_cache = json.load(f)
        except Exception as exc:
            print(f"Warning: Could not parse existing cache, starting fresh: {exc}")

    # 4. Insert or update entry
    demo_cache[image_hash] = cleaned_analysis

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(demo_cache, f, indent=2, ensure_ascii=False)

    print(f"SUCCESS: Added/updated cache entry in '{cache_path}'")
    print(f"  • Item:   {cleaned_analysis['item']}")
    print(f"  • Route:  {cleaned_analysis['route']}")
    print(f"  • Total cached items: {len(demo_cache)}")


if __name__ == "__main__":
    main()
