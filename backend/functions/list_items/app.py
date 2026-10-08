"""
list_items/app.py
-----------------
Lambda handler for GET /items.

Scans the entire DynamoDB table (paginated), sorts items by created_at
descending, and returns up to 100 newest items as:

    {"items": [...]}

Returns an empty list when the table is empty.
DynamoDB Decimal values are converted to int/float before serialisation.
"""

import json
import logging
import os
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# ── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Constants ─────────────────────────────────────────────────────────────────
TABLE_NAME = os.environ["TABLE_NAME"]
MAX_ITEMS = 100

# ── Helpers ───────────────────────────────────────────────────────────────────

def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": _cors_headers(),
        "body": json.dumps(body, default=_decimal_converter),
    }


def _decimal_converter(obj):
    """JSON serialiser hook: convert Decimal → int or float."""
    if isinstance(obj, Decimal):
        # Preserve integer Decimals as int, fractional as float.
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


def _scan_all(table) -> list:
    """Full table scan, following pagination until done."""
    items = []
    kwargs: dict = {}
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        last = response.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return items


# ── Handler ───────────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context) -> dict:  # noqa: ANN001
    logger.info("GET /items invoked")

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    try:
        all_items = _scan_all(table)
    except ClientError as exc:
        logger.exception("DynamoDB scan failed: %s", exc.response["Error"]["Message"])
        return _response(500, {"error": "Internal error"})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during scan: %s", exc)
        return _response(500, {"error": "Internal error"})

    # Sort newest first, then take at most MAX_ITEMS.
    # created_at is ISO-8601 UTC so lexicographic sort is correct.
    all_items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    result = all_items[:MAX_ITEMS]

    logger.info("Returning %d item(s)", len(result))
    return _response(200, {"items": result})
