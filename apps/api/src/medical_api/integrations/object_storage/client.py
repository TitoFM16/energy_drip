import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

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
    """A separate client for presigning only. SigV4 signs the `Host`
    header, so a URL presigned against the internal Docker-network client
    (endpoint_url=http://minio:9000) fails signature validation the moment
    a browser requests it from http://localhost:9000 instead — the client
    used to presign has to be built against the same host the caller will
    actually hit.
    """
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint_url or settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists() -> None:
    """Creates the configured bucket if it's missing.

    Dev/test convenience only — call sites gate this on `not
    settings.is_production` (see `main.py`'s lifespan). A production bucket
    should be provisioned by infrastructure with its own lifecycle,
    versioning, and access policy, not created ad hoc by the app on boot
    with whatever permissions its runtime credentials happen to have.
    """
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code not in ("404", "NoSuchBucket"):
            raise
        client.create_bucket(Bucket=settings.s3_bucket)


def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    client = get_s3_client()
    client.put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)


def download_bytes(key: str) -> bytes:
    client = get_s3_client()
    return client.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()


def generate_presigned_download_url(key: str, expires_in: int = 300) -> str:
    client = get_s3_public_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
