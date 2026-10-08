"""
get_item/app.py
---------------
Lambda handler for GET /items/{id}.

Reads `id` from pathParameters, fetches the item from DynamoDB and returns:
    200  – the Item object
    400  – {"error":"..."} if id is invalid
    404  – {"error":"Item not found"} if id does not exist in the table
    500  – {"error":"Internal error"} on unexpected failures

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
MAX_ID_LENGTH = 64

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
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


# ── Handler ───────────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context) -> dict:  # noqa: ANN001
    logger.info("GET /items/{id} invoked")

    # ── Validate id ───────────────────────────────────────────────────────────
    path_params = event.get("pathParameters") or {}
    item_id = path_params.get("id", "")

    if not item_id:
        return _response(400, {"error": "Missing path parameter: id"})

    if not isinstance(item_id, str) or len(item_id) > MAX_ID_LENGTH:
        return _response(
            400,
            {"error": f"Invalid id: must be a non-empty string of at most {MAX_ID_LENGTH} characters"},
        )

    logger.info("Looking up item id (length=%d)", len(item_id))

    # ── Fetch from DynamoDB ───────────────────────────────────────────────────
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    try:
        db_response = table.get_item(Key={"id": item_id})
    except ClientError as exc:
        logger.exception("DynamoDB get_item failed: %s", exc.response["Error"]["Message"])
        return _response(500, {"error": "Internal error"})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during get_item: %s", exc)
        return _response(500, {"error": "Internal error"})

    item = db_response.get("Item")
    if item is None:
        logger.info("Item not found")
        return _response(404, {"error": "Item not found"})

    logger.info("Item found, returning response")
    return _response(200, item)
