"""
analyze/app.py
--------------
Lambda handler for POST /analyze.

Validates input size & magic bytes, delegates analysis to pipeline.py or mock_result,
persists the resulting Item to DynamoDB, emits structured JSON logs, and returns the Item JSON.
"""

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from logic import (
    detect_image_type,
    mock_result,
)
from pipeline import (
    AnalysisError,
    run_analysis,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Constants & Environment ──────────────────────────────────────────────────
BUCKET_NAME = os.environ.get("BUCKET_NAME", "")
TABLE_NAME = os.environ.get("TABLE_NAME", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "")
USE_MOCK = os.environ.get("USE_MOCK", "false").lower() == "true"

MAX_BODY_BYTES = 2048                     # 2 KB body limit
MAX_IMAGE_BYTES = int(3.5 * 1024 * 1024)  # 3.5 MB image limit
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

CACHE_FILE = os.path.join(os.path.dirname(__file__), "demo_cache.json")
try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        DEMO_CACHE = json.load(f)
except Exception as exc:  # noqa: BLE001
    logger.warning("Could not load demo_cache.json: %s", exc)
    DEMO_CACHE = {}

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


def _log_record(
    request_id: str | None,
    mode: str,
    source: str | None,
    route: str | None,
    confidence: float | None,
    start_time: float,
    error_type: str | None = None,
) -> None:
    """Emit exactly one structured JSON log line per request."""
    latency_ms = round((time.time() - start_time) * 1000, 2)
    record = {
        "request_id": request_id or "unknown",
        "mode": mode,
        "source": source,
        "route": route,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "error_type": error_type,
    }
    logger.info(json.dumps(record))


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
    start_time = time.time()
    request_id = getattr(context, "aws_request_id", None) if context else None
    mode = "mock" if USE_MOCK else "real"

    raw_body = event.get("body") or ""

    # 1. Reject request bodies over 2 KB
    if len(raw_body.encode("utf-8")) > MAX_BODY_BYTES:
        _log_record(request_id, mode, None, None, None, start_time, error_type="body_too_large")
        return _response(400, {"error": "Request body too large"})

    # 2. Parse & Validate Request Body
    try:
        body = json.loads(raw_body or "{}")
    except (json.JSONDecodeError, TypeError) as exc:
        _log_record(request_id, mode, None, None, None, start_time, error_type="bad_json")
        return _response(400, {"error": f"Invalid JSON body: {exc}"})

    if not isinstance(body, dict):
        _log_record(request_id, mode, None, None, None, start_time, error_type="body_not_object")
        return _response(400, {"error": "Request body must be a JSON object"})

    image_key = body.get("image_key")
    if not image_key or not isinstance(image_key, str):
        _log_record(request_id, mode, None, None, None, start_time, error_type="missing_image_key")
        return _response(400, {"error": "Missing required field: image_key"})

    if not IMAGE_KEY_REGEX.match(image_key):
        _log_record(request_id, mode, None, None, None, start_time, error_type="invalid_image_key")
        return _response(
            400,
            {"error": "Invalid image_key: must match format uploads/<name>.(jpg|jpeg|png|webp)"},
        )

    # 3. Branch: Mock Mode vs Real Mode
    if USE_MOCK:
        logger.info("MOCK MODE")
        source = "mock"
        analysis = mock_result(image_key)
    else:
        # a. head_object to verify existence and check size
        try:
            head_resp = s3_client.head_object(Bucket=BUCKET_NAME, Key=image_key)
        except ClientError as exc:
            err_code = exc.response.get("Error", {}).get("Code", "")
            if err_code in ("404", "NoSuchKey", "NotFound"):
                _log_record(request_id, mode, None, None, None, start_time, error_type="image_not_found")
                return _response(404, {"error": "Image not found"})
            logger.error("S3 head_object error (%s)", err_code)
            _log_record(request_id, mode, None, None, None, start_time, error_type="s3_head_error")
            return _response(500, {"error": "Failed to verify image"})
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected S3 error: %s", exc)
            _log_record(request_id, mode, None, None, None, start_time, error_type="s3_head_unexpected")
            return _response(500, {"error": "Failed to verify image"})

        content_length = head_resp.get("ContentLength", 0)
        if content_length > MAX_IMAGE_BYTES:
            _log_record(request_id, mode, None, None, None, start_time, error_type="image_too_large")
            return _response(413, {"error": "Image too large"})

        # b. get_object and read bytes
        try:
            s3_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=image_key)
            image_bytes = s3_obj["Body"].read()
        except ClientError as exc:
            err_code = exc.response.get("Error", {}).get("Code", "")
            logger.error("S3 get_object error (%s)", err_code)
            _log_record(request_id, mode, None, None, None, start_time, error_type="s3_get_error")
            return _response(500, {"error": "Failed to retrieve image"})
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error reading image: %s", exc)
            _log_record(request_id, mode, None, None, None, start_time, error_type="s3_get_unexpected")
            return _response(500, {"error": "Failed to retrieve image"})

        # c. Verify magic bytes match file extension
        ext = image_key.rsplit(".", 1)[-1].lower()
        expected_type = FORMAT_MAP.get(ext)
        detected_type = detect_image_type(image_bytes)

        if not detected_type or detected_type != expected_type:
            _log_record(request_id, mode, None, None, None, start_time, error_type="invalid_magic_bytes")
            return _response(400, {"error": "File is not a valid image"})

        # d. Verify Bedrock Model ID
        model_id = os.environ.get("BEDROCK_MODEL_ID") or BEDROCK_MODEL_ID
        if not model_id:
            logger.error("BEDROCK_MODEL_ID is empty")
            _log_record(request_id, mode, None, None, None, start_time, error_type="model_not_configured")
            return _response(500, {"error": "Model not configured"})

        # e. Run Analysis via pipeline
        try:
            analysis, source = run_analysis(
                bedrock_client=bedrock_client,
                model_id=model_id,
                system_prompt=SYSTEM_PROMPT,
                image_bytes=image_bytes,
                image_format=detected_type,
                demo_cache=DEMO_CACHE,
            )
        except AnalysisError as exc:
            logger.error("Analysis failed: %s", exc)
            _log_record(request_id, mode, None, None, None, start_time, error_type="analysis_error")
            return _response(502, {"error": "Analysis failed"})
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in analysis pipeline: %s", type(exc).__name__)
            _log_record(request_id, mode, None, None, None, start_time, error_type="pipeline_unexpected")
            return _response(502, {"error": "Analysis failed"})

    # 4. Construct Item Object (Strictly contract fields only)
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

    # 5. Persist to DynamoDB
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=_to_dynamodb_item(item))
    except ClientError as exc:
        err_code = exc.response.get("Error", {}).get("Code", "")
        logger.error("DynamoDB put_item ClientError (%s)", err_code)
        _log_record(request_id, mode, source, item["route"], item["confidence"], start_time, error_type="dynamodb_error")
        return _response(500, {"error": "Internal error"})
    except Exception as exc:  # noqa: BLE001
        logger.error("DynamoDB put_item unexpected error: %s", type(exc).__name__)
        _log_record(request_id, mode, source, item["route"], item["confidence"], start_time, error_type="dynamodb_unexpected")
        return _response(500, {"error": "Internal error"})

    # 6. Structured success log & response
    _log_record(request_id, mode, source, item["route"], item["confidence"], start_time, error_type=None)
    return _response(200, item)
