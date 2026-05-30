from __future__ import annotations

"""Object storage helpers for export artifacts (S3/MinIO)."""


import asyncio
from dataclasses import dataclass
from functools import lru_cache

from botocore.client import BaseClient
from botocore.config import Config

from ..config.settings import get_settings


@dataclass(frozen=True)
class StoredObject:
    """Metadata describing a stored object."""

    bucket: str
    key: str
    etag: str | None


@lru_cache(maxsize=1)
def _s3_client() -> BaseClient:
    """Create a singleton S3-compatible client for object storage."""
    session_kwargs = {
        "aws_access_key_id": get_settings().export_storage_access_key,
        "aws_secret_access_key": get_settings().export_storage_secret_key,
        "region_name": get_settings().export_storage_region,
    }

    import boto3

    return boto3.client(
        "s3",
        endpoint_url=get_settings().export_storage_endpoint,
        use_ssl=get_settings().export_storage_use_ssl,
        config=Config(signature_version="s3v4"),
        **session_kwargs,
    )


async def upload_bytes(
    *,
    object_key: str,
    content: bytes,
    content_type: str,
    metadata: dict[str, str] | None = None,
) -> StoredObject:
    """Upload bytes to configured S3/MinIO bucket."""
    client = _s3_client()

    def _upload() -> dict:
        return client.put_object(
            Bucket=get_settings().export_storage_bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type,
            Metadata=metadata or {},
        )

    result = await asyncio.to_thread(_upload)
    etag = result.get("ETag")
    return StoredObject(bucket=get_settings().export_storage_bucket, key=object_key, etag=etag)


async def generate_download_url(*, object_key: str, expires_in_seconds: int | None = None) -> str:
    """Generate short-lived signed GET URL for a stored object."""
    client = _s3_client()
    expiry = expires_in_seconds or get_settings().export_signed_url_ttl_seconds

    def _sign() -> str:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": get_settings().export_storage_bucket, "Key": object_key},
            ExpiresIn=expiry,
        )

    return await asyncio.to_thread(_sign)
