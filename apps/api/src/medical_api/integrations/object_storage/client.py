"""Private consent storage: a persistent local directory, or optional S3."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from jose import JWTError, jwt

from medical_api.core.config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )


def get_s3_public_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint_url or settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )


def local_path(key: str) -> Path:
    root = settings.private_storage_path.resolve()
    path = (root / key).resolve()
    if not key or path == root or not path.is_relative_to(root):
        raise ValueError("Invalid storage key")
    return path


def ensure_bucket_exists() -> None:
    if settings.storage_backend == "local":
        settings.private_storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if settings.is_production or error_code not in ("404", "NoSuchBucket"):
            raise
        client.create_bucket(Bucket=settings.s3_bucket)


def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    if settings.storage_backend == "s3":
        get_s3_client().put_object(
            Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type
        )
        return
    path = local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Keys are immutable UUIDs. A failed write never overwrites a signed record.
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)


def download_bytes(key: str) -> bytes:
    if settings.storage_backend == "local":
        return local_path(key).read_bytes()
    return get_s3_client().get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()


def generate_presigned_download_url(key: str, expires_in: int = 300) -> str:
    if settings.storage_backend == "s3":
        return get_s3_public_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    token = jwt.encode(
        {
            "key": key,
            "aud": "consent-download",
            "exp": datetime.now(UTC) + timedelta(seconds=expires_in),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return f"/api/v1/documents/content/{token}"


def resolve_download_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience="consent-download",
            options={"require_exp": True},
        )
        key = payload["key"]
        if not isinstance(key, str) or not key.endswith(".pdf"):
            raise ValueError("Invalid document key")
        local_path(key)
        return key
    except (JWTError, KeyError, ValueError, TypeError) as exc:
        raise ValueError("Invalid or expired download link") from exc
