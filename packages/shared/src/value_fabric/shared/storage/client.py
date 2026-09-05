"""S3-compatible storage client implementation."""

from __future__ import annotations

import os
import re
from typing import Any, AsyncIterator, Optional
from urllib.parse import urljoin

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Server-side maximum TTL for presigned (signed) URLs. Clients may request a
# shorter expiry but may never exceed this bound; the value is enforced
# server-side so URL lifetime is not client-controllable.
MAX_PRESIGNED_URL_EXPIRY_SECONDS = int(
    os.getenv("MAX_PRESIGNED_URL_EXPIRY_SECONDS", "3600")
)

# Tenant ids may only contain URL/path-safe characters. Anything containing
# separators, traversal segments, whitespace, or NUL bytes is refused so a
# tenant id can never be used to escape the tenant prefix boundary.
_TENANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def _validate_tenant_id(tenant_id: str) -> None:
    """Fail closed on tenant ids that could escape the prefix boundary."""
    if not _TENANT_ID_PATTERN.match(tenant_id):
        raise ValueError("invalid tenant id for storage scoping")


def _validate_object_key(key: str) -> None:
    """Fail closed on object keys containing path-traversal segments."""
    if "\x00" in key or "\\" in key:
        raise ValueError("invalid object key")
    segments = key.split("/")
    if any(segment == ".." for segment in segments):
        raise ValueError("object key must not contain traversal segments")


class StorageClient:
    """S3-compatible storage client with tenant-scoped object keys."""

    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        region: str = "us-east-1",
        encryption: str = "AES256",
    ) -> None:
        """Initialize storage client.

        Args:
            endpoint_url: S3 endpoint URL (e.g., http://localhost:9000 for MinIO)
            access_key_id: Access key ID
            secret_access_key: Secret access key
            bucket: Bucket name
            region: AWS region (for S3)
            encryption: Server-side encryption algorithm (AES256 or aws:kms)
        """
        self.bucket = bucket
        self.encryption = encryption

        config = Config(
            region_name=region,
            signature_version="s3v4",
        )

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=config,
        )

    def _normalize_key(self, key: str, tenant_id: Optional[str] = None) -> str:
        """Normalize object key with tenant prefix.

        Args:
            key: Object key (e.g., "documents/file.pdf")
            tenant_id: Tenant ID for scoping

        Returns:
            Normalized key with tenant prefix (e.g., "tenant-123/documents/file.pdf")
        """
        stripped = key.lstrip('/')
        _validate_object_key(stripped)
        if tenant_id:
            _validate_tenant_id(tenant_id)
            return f"tenant-{tenant_id}/{stripped}"
        return stripped

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        tenant_id: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> bool:
        """Upload object to storage.

        Args:
            key: Object key
            data: Object data
            content_type: Content type
            tenant_id: Tenant ID for scoping
            metadata: Optional metadata

        Returns:
            True if successful, False otherwise
        """
        normalized_key = self._normalize_key(key, tenant_id)

        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=normalized_key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption=self.encryption,
                Metadata=metadata or {},
            )
            return True
        except ClientError as e:
            print(f"Failed to upload object {normalized_key}: {e}")
            return False

    async def get_object(self, key: str, tenant_id: Optional[str] = None) -> Optional[bytes]:
        """Download object from storage.

        Args:
            key: Object key
            tenant_id: Tenant ID for scoping

        Returns:
            Object data if found, None otherwise
        """
        normalized_key = self._normalize_key(key, tenant_id)

        try:
            response = self._client.get_object(
                Bucket=self.bucket,
                Key=normalized_key,
            )
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            print(f"Failed to download object {normalized_key}: {e}")
            return None

    async def delete_object(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """Delete object from storage.

        Args:
            key: Object key
            tenant_id: Tenant ID for scoping

        Returns:
            True if successful, False otherwise
        """
        normalized_key = self._normalize_key(key, tenant_id)

        try:
            self._client.delete_object(
                Bucket=self.bucket,
                Key=normalized_key,
            )
            return True
        except ClientError as e:
            print(f"Failed to delete object {normalized_key}: {e}")
            return False

    async def list_objects(
        self,
        prefix: str = "",
        tenant_id: Optional[str] = None,
    ) -> list[str]:
        """List objects with given prefix.

        Args:
            prefix: Object key prefix
            tenant_id: Tenant ID for scoping

        Returns:
            List of object keys
        """
        normalized_prefix = self._normalize_key(prefix, tenant_id)

        try:
            response = self._client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=normalized_prefix,
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            print(f"Failed to list objects with prefix {normalized_prefix}: {e}")
            return []

    async def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        tenant_id: Optional[str] = None,
    ) -> Optional[str]:
        """Generate presigned URL for object access.

        Args:
            key: Object key
            expires_in: URL expiration time in seconds
            tenant_id: Tenant ID for scoping

        Returns:
            Presigned URL if successful, None otherwise
        """
        normalized_key = self._normalize_key(key, tenant_id)

        # Enforce the server-side TTL bound; fail closed on out-of-range or
        # non-positive expiries so URL lifetime is never client-controllable.
        if not isinstance(expires_in, int) or isinstance(expires_in, bool):
            raise ValueError("expires_in must be an integer number of seconds")
        if expires_in <= 0:
            raise ValueError("expires_in must be positive")
        if expires_in > MAX_PRESIGNED_URL_EXPIRY_SECONDS:
            raise ValueError(
                "expires_in exceeds the server-side maximum of "
                f"{MAX_PRESIGNED_URL_EXPIRY_SECONDS} seconds"
            )

        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": normalized_key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            print(f"Failed to generate presigned URL for {normalized_key}: {e}")
            return None

    async def object_exists(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """Check if object exists.

        Args:
            key: Object key
            tenant_id: Tenant ID for scoping

        Returns:
            True if object exists, False otherwise
        """
        normalized_key = self._normalize_key(key, tenant_id)

        try:
            self._client.head_object(
                Bucket=self.bucket,
                Key=normalized_key,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            print(f"Failed to check existence of {normalized_key}: {e}")
            return False


# Global client instance
_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """Get or create global storage client instance.

    Reads configuration from environment variables:
    - STORAGE_TYPE: "local" (MinIO) or "s3" (AWS S3)
    - S3_ENDPOINT: S3 endpoint URL
    - S3_ACCESS_KEY_ID: Access key ID
    - S3_SECRET_ACCESS_KEY: Secret access key
    - S3_BUCKET: Bucket name
    - S3_REGION: AWS region (default: us-east-1)

    Returns:
        StorageClient instance
    """
    global _client

    if _client is not None:
        return _client

    storage_type = os.getenv("STORAGE_TYPE", "local")

    if storage_type == "local":
        # MinIO configuration
        endpoint_url = os.getenv("S3_ENDPOINT", "http://localhost:9000")
        access_key_id = os.getenv("S3_ACCESS_KEY_ID", "minioadmin")
        secret_access_key = os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin")
        bucket = os.getenv("S3_BUCKET", "fabric4l")
        region = os.getenv("S3_REGION", "us-east-1")
    else:
        # AWS S3 configuration
        endpoint_url = os.getenv("S3_ENDPOINT", "https://s3.amazonaws.com")
        access_key_id = os.getenv("S3_ACCESS_KEY_ID")
        secret_access_key = os.getenv("S3_SECRET_ACCESS_KEY")
        bucket = os.getenv("S3_BUCKET")
        region = os.getenv("S3_REGION", "us-east-1")

        if not access_key_id or not secret_access_key or not bucket:
            raise ValueError(
                "S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, and S3_BUCKET must be set for S3 storage"
            )

    _client = StorageClient(
        endpoint_url=endpoint_url,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        bucket=bucket,
        region=region,
    )

    return _client
