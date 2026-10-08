"""
upload_url/app.py
-----------------
Lambda handler for POST /upload-url.

Expects JSON body:
    { "filename": "foo.jpg", "content_type": "image/jpeg" }

Returns:
    200  { "upload_url": "<presigned S3 PUT URL>", "image_key": "uploads/<uuid>.jpg" }
    400  { "error": "<reason>" }
"""

import json
import logging
import os
import uuid

import boto3
from botocore.exceptions import ClientError

# ── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Constants ─────────────────────────────────────────────────────────────────
BUCKET_NAME = os.environ["BUCKET_NAME"]

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

PRESIGN_EXPIRY_SECONDS = 300  # 5 minutes

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
        "body": json.dumps(body),
    }


def _error(status_code: int, message: str) -> dict:
    logger.error("Returning %s: %s", status_code, message)
    return _response(status_code, {"error": message})


# ── Handler ───────────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context) -> dict:  # noqa: ANN001
    logger.info("Event: %s", json.dumps(event))

    # ── Parse body ────────────────────────────────────────────────────────────
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError) as exc:
        return _error(400, f"Invalid JSON body: {exc}")

    filename = body.get("filename")
    content_type = body.get("content_type")

    if not filename:
        return _error(400, "Missing required field: filename")
    if not content_type:
        return _error(400, "Missing required field: content_type")

    # ── Validate content type ─────────────────────────────────────────────────
    extension = ALLOWED_CONTENT_TYPES.get(content_type)
    if extension is None:
        return _error(
            400,
            f"Unsupported content_type '{content_type}'. "
            f"Allowed values: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # ── Build the S3 key ──────────────────────────────────────────────────────
    image_key = f"uploads/{uuid.uuid4()}{extension}"

    # ── Generate presigned PUT URL ────────────────────────────────────────────
    s3_client = boto3.client("s3")
    try:
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": image_key,
                "ContentType": content_type,
            },
            ExpiresIn=PRESIGN_EXPIRY_SECONDS,
        )
    except ClientError as exc:
        logger.exception("Failed to generate presigned URL: %s", exc)
        return _error(500, "Could not generate upload URL. Please try again.")

    logger.info("Generated presigned URL for key: %s", image_key)

    return _response(200, {"upload_url": upload_url, "image_key": image_key})
