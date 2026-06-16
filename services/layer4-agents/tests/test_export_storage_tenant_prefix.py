import pytest

from layer4_agents.services.export_storage import _tenant_key, upload_bytes


def test_tenant_key_rejects_missing_tenant():
    with pytest.raises(ValueError, match="tenant_id is required"):
        _tenant_key("", "file.pdf")


def test_tenant_key_rejects_path_traversal():
    with pytest.raises(ValueError, match="object_key must be a relative path"):
        _tenant_key("tenant-123", "../other/file.pdf")
    with pytest.raises(ValueError, match="object_key must be a relative path"):
        _tenant_key("tenant-123", "/absolute/file.pdf")


def test_tenant_key_prefixes_relative_path():
    assert _tenant_key("tenant-123", "file.pdf") == "tenant-123/file.pdf"
    assert _tenant_key("tenant-123", "exports/file.pdf") == "tenant-123/exports/file.pdf"


def test_tenant_key_idempotent_prefix():
    assert _tenant_key("tenant-123", "tenant-123/file.pdf") == "tenant-123/file.pdf"


async def test_upload_rejects_key_without_tenant_prefix():
    with pytest.raises(ValueError, match="tenant_id is required"):
        await upload_bytes(tenant_id="", object_key="exports/file.pdf", content=b"x", content_type="application/pdf")
