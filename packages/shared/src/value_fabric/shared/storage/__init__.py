"""S3-compatible storage abstraction for Fabric_4L.

Provides a unified interface for object storage that works with:
- MinIO (local/dev)
- AWS S3 (production)
- Other S3-compatible services (Azure Blob, GCS via S3 gateway)

Usage:
    from value_fabric.shared.storage import get_storage_client

    storage = get_storage_client()
    await storage.put_object("tenant-123/documents/file.pdf", data)
    data = await storage.get_object("tenant-123/documents/file.pdf")
    url = await storage.generate_presigned_url("tenant-123/documents/file.pdf", expires_in=3600)
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator, Optional

from .client import StorageClient, get_storage_client

__all__ = ["StorageClient", "get_storage_client"]
