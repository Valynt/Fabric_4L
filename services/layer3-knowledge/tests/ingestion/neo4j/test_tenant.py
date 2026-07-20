import pytest

from src.ingestion.neo4j.tenant import (
    TenantValidationError,
    validate_ingestion_tenant_id,
)


def test_validate_ingestion_tenant_id_accepts_uuid():
    assert validate_ingestion_tenant_id("12345678-1234-1234-1234-123456789abc") == (
        "12345678-1234-1234-1234-123456789abc"
    )


def test_validate_ingestion_tenant_id_rejects_missing():
    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        validate_ingestion_tenant_id(None)


def test_validate_ingestion_tenant_id_rejects_empty():
    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        validate_ingestion_tenant_id("   ")


def test_validate_ingestion_tenant_id_rejects_non_uuid():
    with pytest.raises(TenantValidationError, match="Invalid tenant_id format"):
        validate_ingestion_tenant_id("system")
