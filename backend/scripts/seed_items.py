"""
scripts/seed_items.py
---------------------
Inserts 4 demo items into the ReLoop DynamoDB table that satisfy every field
in the CONTRACT.md Item specification.

Usage (PowerShell):
    # Seed (will prompt for confirmation):
    $env:TABLE_NAME = "<your-table-name>"
    python backend/scripts/seed_items.py

    # Or pass the table name directly:
    python backend/scripts/seed_items.py --table <your-table-name>

    # Remove only seeded items (image_key starts with "uploads/seed-"):
    python backend/scripts/seed_items.py --delete
    python backend/scripts/seed_items.py --delete --table <your-table-name>

Rules:
- Table name: TABLE_NAME env var, or --table argument.
- Region:     AWS_REGION env var, or us-east-1.
- confidence stored as Decimal (boto3 rejects float).
- No hardcoded names, keys, or account IDs.

NOTE: The Telugu text below is a machine-translated placeholder.
      Please ask Member A to verify / replace before the demo.
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# ── Telugu placeholder steps (to be reviewed by Member A) ────────────────────
STEPS_EN_HAZARD = [
    "Keep away from heat",
    "Do not put in a bin",
    "Hand over to campus e-waste staff",
]
STEPS_TE_HAZARD = [
    "వేడికి దూరంగా ఉంచండి",          # Keep away from heat
    "చెత్తబుట్టలో వేయకండి",             # Do not put in a bin
    "క్యాంపస్ ఈ-వేస్ట్ సిబ్బందికి అప్పగించండి",  # Hand over to campus e-waste staff
]

STEPS_EN_REPAIR = [
    "Back up your data before repair",
    "Take to an authorised repair centre",
    "Do not attempt self-repair",
]
STEPS_TE_REPAIR = [
    "మరమ్మత్తు ముందు మీ డేటాను బ్యాకప్ చేయండి",
    "అధికారిక రిపేర్ సెంటర్‌కు తీసుకెళ్ళండి",
    "స్వయంగా మరమ్మత్తు చేయడానికి ప్రయత్నించకండి",
]

STEPS_EN_RECYCLE = [
    "Do not put in household rubbish",
    "Drop off at the campus e-waste collection point",
]
STEPS_TE_RECYCLE = [
    "గృహ చెత్తలో వేయకండి",
    "క్యాంపస్ ఈ-వేస్ట్ సేకరణ కేంద్రంలో వదలండి",
]

# ── Seed items ────────────────────────────────────────────────────────────────
def _now_minus(hours: float) -> str:
    """Return an ISO-8601 UTC timestamp `hours` ago."""
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_seed_items() -> list[dict]:
    return [
        # 1 – Hazard: swollen power bank (high confidence)
        {
            "id": str(uuid.uuid4()),
            "image_key": "uploads/seed-1.jpg",
            "created_at": _now_minus(0.5),
            "item": "power bank",
            "condition": "damaged",
            "battery_risk": "high",
            "swollen_battery": True,
            "route": "hazard",
            "confidence": Decimal("0.82"),
            "reason": "Battery casing looks bulged and deformed, indicating swelling.",
            "safe_steps_en": STEPS_EN_HAZARD,
            "safe_steps_te": STEPS_TE_HAZARD,
            "status": "reported",
        },
        # 2 – Hazard: visible battery, low-confidence rule fires (confidence < 0.6)
        {
            "id": str(uuid.uuid4()),
            "image_key": "uploads/seed-2.jpg",
            "created_at": _now_minus(1.5),
            "item": "lithium battery",
            "condition": "worn",
            "battery_risk": "medium",
            "swollen_battery": False,
            "route": "hazard",           # low-confidence rule: battery visible + conf < 0.6
            "confidence": Decimal("0.45"),
            "reason": "Battery visible but image unclear; routed to hazard as a precaution.",
            "safe_steps_en": STEPS_EN_HAZARD,
            "safe_steps_te": STEPS_TE_HAZARD,
            "status": "reported",
        },
        # 3 – Repair: cracked phone screen
        {
            "id": str(uuid.uuid4()),
            "image_key": "uploads/seed-3.jpg",
            "created_at": _now_minus(3.0),
            "item": "smartphone",
            "condition": "damaged",
            "battery_risk": "low",
            "swollen_battery": False,
            "route": "repair",
            "confidence": Decimal("0.91"),
            "reason": "Screen is cracked but the device is otherwise functional.",
            "safe_steps_en": STEPS_EN_REPAIR,
            "safe_steps_te": STEPS_TE_REPAIR,
            "status": "reported",
        },
        # 4 – Recycle: old keyboard (no battery)
        {
            "id": str(uuid.uuid4()),
            "image_key": "uploads/seed-4.jpg",
            "created_at": _now_minus(5.0),
            "item": "keyboard",
            "condition": "worn",
            "battery_risk": "none",
            "swollen_battery": False,
            "route": "recycle",
            "confidence": Decimal("0.95"),
            "reason": "Keyboard is old and heavily worn; no battery present.",
            "safe_steps_en": STEPS_EN_RECYCLE,
            "safe_steps_te": STEPS_TE_RECYCLE,
            "status": "reported",
        },
    ]


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed or clean ReLoop demo data.")
    parser.add_argument(
        "--table",
        default=os.environ.get("TABLE_NAME", ""),
        help="DynamoDB table name (overrides TABLE_NAME env var)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete only seeded items (image_key starts with 'uploads/seed-')",
    )
    return parser.parse_args()


def get_table(table_name: str, region: str):
    dynamodb = boto3.resource("dynamodb", region_name=region)
    return dynamodb.Table(table_name)


def seed(table, items: list[dict]) -> None:
    print(f"Inserting {len(items)} item(s)...")
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
            print(f"  ✓ {item['image_key']}  route={item['route']}  id={item['id']}")
    print("Seed complete.")


def delete_seeded(table) -> None:
    print("Scanning for seeded items (image_key starts with 'uploads/seed-')...")
    items = []
    kwargs: dict = {"FilterExpression": Attr("image_key").begins_with("uploads/seed-")}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last

    if not items:
        print("No seeded items found.")
        return

    print(f"Found {len(items)} seeded item(s) to delete:")
    for item in items:
        print(f"  • {item['image_key']}  id={item['id']}")

    confirm = input("Type 'yes' to delete them: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"id": item["id"]})
            print(f"  ✗ deleted {item['image_key']}")
    print("Delete complete.")


def main() -> None:
    args = parse_args()
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not args.table:
        print("ERROR: Table name not provided. Set TABLE_NAME env var or use --table.", file=sys.stderr)
        sys.exit(1)

    print(f"Table : {args.table}")
    print(f"Region: {region}")

    table = get_table(args.table, region)

    if args.delete:
        delete_seeded(table)
        return

    # ── Seed path ──────────────────────────────────────────────────────────────
    items = build_seed_items()
    print(f"\nAbout to insert {len(items)} demo items into '{args.table}'.")
    confirm = input("Type 'yes' to continue: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    try:
        seed(table, items)
    except ClientError as exc:
        print(f"ERROR: {exc.response['Error']['Message']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
