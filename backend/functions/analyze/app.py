"""
analyze/app.py
--------------
Lambda handler for POST /analyze.

Analyzes an uploaded image via AWS Bedrock (or mock mode if USE_MOCK="true"),
enforces contract safety rules, persists the resulting Item to DynamoDB,
and returns the Item JSON.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from logic import (
    apply_safety_rules,
    extract_json,
    mock_result,
    validate_and_normalize,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Constants & Environment ──────────────────────────────────────────────────
BUCKET_NAME = os.environ.get("BUCKET_NAME", "")
TABLE_NAME = os.environ.get("TABLE_NAME", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "")
USE_MOCK = os.environ.get("USE_MOCK", "false").lower() == "true"

MAX_IMAGE_BYTES = int(3.5 * 1024 * 1024)  # 3.5 MB
IMAGE_KEY_REGEX = re.compile(r"^uploads/[A-Za-z0-9._-]+\.(jpg|jpeg|png|webp)$")

FORMAT_MAP = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "png": "png",
    "webp": "webp",
}

# ── Cold Start Initialization ────────────────────────────────────────────────
PROMPT_FILE = os.path.join(os.path.dirname(__file__), "prompt.txt")
try:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read().strip()
except Exception as exc:  # noqa: BLE001
    logger.warning("Could not read prompt.txt: %s", exc)
    SYSTEM_PROMPT = ""

boto_config = Config(read_timeout=25, retries={"max_attempts": 1})
bedrock_client = boto3.client("bedrock-runtime", config=boto_config)
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


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
        "body": json.dumps(body, default=_decimal_serializer),
    }


def _decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _error(status_code: int, message: str) -> dict:
    logger.error("Returning %d: %s", status_code, message)
    return _response(status_code, {"error": message})


def _to_dynamodb_item(item: dict) -> dict:
    """Convert float values (like confidence) to Decimal for DynamoDB."""
    ddb_item = {}
    for k, v in item.items():
        if isinstance(v, float):
            ddb_item[k] = Decimal(str(v))
        else:
            ddb_item[k] = v
    return ddb_item


# ── Handler ───────────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context) -> dict:  # noqa: ANN001
    logger.info("POST /analyze invoked")

    # ── Parse & Validate Request Body ─────────────────────────────────────────
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError) as exc:
        return _error(400, f"Invalid JSON body: {exc}")

    if not isinstance(body, dict):
        return _error(400, "Request body must be a JSON object")

    image_key = body.get("image_key")
    if not image_key or not isinstance(image_key, str):
        return _error(400, "Missing required field: image_key")

    if not IMAGE_KEY_REGEX.match(image_key):
        return _error(
            400,
            "Invalid image_key: must match format uploads/<name>.(jpg|jpeg|png|webp)",
        )

    # ── Execution Branch: Mock vs Real Bedrock ─────────────────────────────────
    if USE_MOCK:
        logger.info("MOCK MODE: returning mock analysis for %s", image_key)
        analysis = mock_result(image_key)
    else:
        # Real flow
        # a. head_object to verify existence and check size
        try:
            head_resp = s3_client.head_object(Bucket=BUCKET_NAME, Key=image_key)
        except ClientError as exc:
            err_code = exc.response.get("Error", {}).get("Code", "")
            if err_code in ("404", "NoSuchKey", "NotFound"):
                return _error(404, "Image not found")
            logger.error("S3 head_object error (%s)", err_code)
            return _error(500, "Failed to verify image")
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected S3 error: %s", exc)
            return _error(500, "Failed to verify image")

        content_length = head_resp.get("ContentLength", 0)
        logger.info("Image size: %d bytes", content_length)
        if content_length > MAX_IMAGE_BYTES:
            return _error(413, "Image too large")

        # b. get_object and read bytes
        try:
            s3_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=image_key)
            image_bytes = s3_obj["Body"].read()
        except ClientError as exc:
            err_code = exc.response.get("Error", {}).get("Code", "")
            logger.error("S3 get_object error (%s)", err_code)
            return _error(500, "Failed to retrieve image")
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error reading image: %s", exc)
            return _error(500, "Failed to retrieve image")

        ext = image_key.rsplit(".", 1)[-1].lower()
        image_format = FORMAT_MAP.get(ext, "jpeg")

        # c. Verify Bedrock Model ID
        model_id = os.environ.get("BEDROCK_MODEL_ID") or BEDROCK_MODEL_ID
        if not model_id:
            logger.error("BEDROCK_MODEL_ID is empty")
            return _error(500, "Model not configured")

        # d. Call Bedrock Converse API
        try:
            system_param = [{"text": SYSTEM_PROMPT}] if SYSTEM_PROMPT else []
            bedrock_resp = bedrock_client.converse(
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
        except ClientError as exc:
            err_code = exc.response.get("Error", {}).get("Code", "")
            logger.error("Bedrock converse ClientError (%s)", err_code)
            return _error(502, "Analysis failed")
        except Exception as exc:  # noqa: BLE001
            logger.error("Bedrock converse unexpected error: %s", type(exc).__name__)
            return _error(502, "Analysis failed")

        # Extract text from Converse response
        output_msg = bedrock_resp.get("output", {}).get("message", {})
        content_blocks = output_msg.get("content", [])
        response_text = "".join(b.get("text", "") for b in content_blocks if "text" in b)

        # e. Extract, validate, normalize, and apply safety rules
        try:
            raw_json = extract_json(response_text)
            normalized = validate_and_normalize(raw_json)
            analysis = apply_safety_rules(normalized)
        except ValueError as exc:
            logger.error("Model output processing error: %s", exc)
            return _error(502, "Analysis failed")

    # ── Construct Item Object ─────────────────────────────────────────────────
    item_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    item = {
        "id": item_id,
        "image_key": image_key,
        "created_at": created_at,
        "item": analysis["item"],
        "condition": analysis["condition"],
        "battery_risk": analysis["battery_risk"],
        "swollen_battery": analysis["swollen_battery"],
        "route": analysis["route"],
        "confidence": analysis["confidence"],
        "reason": analysis["reason"],
        "safe_steps_en": analysis["safe_steps_en"],
        "safe_steps_te": analysis["safe_steps_te"],
        "status": "reported",
    }

    logger.info("Classified item %s as route='%s'", item_id, item["route"])

    # ── Save to DynamoDB ──────────────────────────────────────────────────────
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=_to_dynamodb_item(item))
    except ClientError as exc:
        err_code = exc.response.get("Error", {}).get("Code", "")
        logger.error("DynamoDB put_item ClientError (%s)", err_code)
        return _error(500, "Internal error")
    except Exception as exc:  # noqa: BLE001
        logger.error("DynamoDB put_item unexpected error: %s", type(exc).__name__)
        return _error(500, "Internal error")

    return _response(200, item)
