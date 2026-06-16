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


def _tenant_key(tenant_id: str, object_key: str) -> str:
    if not tenant_id:
        raise ValueError("tenant_id is required for S3 operations")
    if not object_key:
        raise ValueError("object_key is required")
    # Reject path traversal and absolute paths.
    if object_key.startswith("/") or ".." in object_key.split("/"):
        raise ValueError(f"object_key must be a relative path: {object_key}")
    # Strip accidental duplicate tenant prefix.
    prefix = f"{tenant_id}/"
    if object_key.startswith(prefix):
        return object_key
    return prefix + object_key


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
    tenant_id: str,
    object_key: str,
    content: bytes,
    content_type: str,
    metadata: dict[str, str] | None = None,
) -> StoredObject:
    """Upload bytes to configured S3/MinIO bucket."""
    key = _tenant_key(tenant_id, object_key)
    client = _s3_client()

    def _upload() -> dict:
        return client.put_object(
            Bucket=get_settings().export_storage_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata=metadata or {},
        )

    result = await asyncio.to_thread(_upload)
    etag = result.get("ETag")
    return StoredObject(bucket=get_settings().export_storage_bucket, key=key, etag=etag)


async def generate_download_url(
    *,
    tenant_id: str,
    object_key: str,
    expires_in_seconds: int | None = None,
) -> str:
    """Generate short-lived signed GET URL for a stored object."""
    key = _tenant_key(tenant_id, object_key)
    client = _s3_client()
    expiry = expires_in_seconds or get_settings().export_signed_url_ttl_seconds

    def _sign() -> str:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": get_settings().export_storage_bucket, "Key": key},
            ExpiresIn=expiry,
        )

    return await asyncio.to_thread(_sign)
