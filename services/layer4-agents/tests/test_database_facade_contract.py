"""Contract tests for the stable Layer 4 database import facade."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import UUID

import pytest

import layer4_agents.database as canonical_database
import layer4_agents.database_facade as database_facade


def test_database_facade_delegates_public_api_to_canonical_module() -> None:
    """The facade must expose the tenant-enforcing canonical implementation."""
    assert database_facade._CANONICAL is not None
    assert database_facade._CANONICAL_IMPORT_ERROR is None
    assert database_facade.get_db_from_context is canonical_database.get_db_from_context
    assert (
        database_facade.get_db_with_optional_tenant
        is canonical_database.get_db_with_optional_tenant
    )
    assert database_facade.get_tiered_db_session is canonical_database.get_tiered_db_session


def test_database_facade_delegates_dynamic_public_attributes() -> None:
    """Late attribute lookup must remain consistent with the canonical module."""
    assert (
        database_facade.__getattr__("validate_tenant_id") is canonical_database.validate_tenant_id
    )


def test_database_facade_fails_closed_when_canonical_module_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing canonical DB implementation must never create an unscoped session."""
    original_import = database_facade.importlib.import_module

    def reject_canonical(name: str):
        if name == "src.database":
            raise ModuleNotFoundError("canonical database unavailable")
        return original_import(name)

    monkeypatch.setattr(database_facade.importlib, "import_module", reject_canonical)
    path = Path(database_facade.__file__)
    spec = importlib.util.spec_from_file_location("_isolated_database_facade", path)
    assert spec is not None and spec.loader is not None
    isolated = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(isolated)

    assert isolated.FAIL_SAFE_MODE is True
    isolated.reset_tenant_validation_metrics()
    tenant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    assert isolated.validate_tenant_id(tenant_id) == str(tenant_id)
    assert isolated.validate_tenant_id(" ADMIN ") == "admin"
    with pytest.raises(isolated.TenantContextError, match="required"):
        isolated.validate_tenant_id(None)
    with pytest.raises(isolated.TenantContextError, match="must not be empty"):
        isolated.validate_tenant_id(" ")
    with pytest.raises(isolated.TenantContextError, match="valid UUID"):
        isolated.validate_tenant_id("not-a-tenant")
    metrics = isolated.get_tenant_validation_metrics()
    assert metrics == {
        "validations_total": 5,
        "validation_failures": 3,
        "uuid_format_errors": 1,
        "missing_context_errors": 1,
        "empty_tenant_errors": 1,
    }
    metrics["validations_total"] = 0
    assert isolated.get_tenant_validation_metrics()["validations_total"] == 5
    with pytest.raises(AttributeError, match="Canonical database module unavailable"):
        isolated.__getattr__("unknown")


@pytest.mark.asyncio
async def test_database_facade_fallback_db_entrypoints_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = database_facade.importlib.import_module

    def reject_canonical(name: str):
        if name == "src.database":
            raise ImportError("missing")
        return original_import(name)

    monkeypatch.setattr(database_facade.importlib, "import_module", reject_canonical)
    spec = importlib.util.spec_from_file_location(
        "_isolated_database_facade_async", Path(database_facade.__file__)
    )
    assert spec is not None and spec.loader is not None
    isolated = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(isolated)

    with pytest.raises(RuntimeError, match="unscoped database session"):
        await isolated.get_db_from_context()
    with pytest.raises(RuntimeError, match="unscoped database session"):
        await isolated.get_db_with_optional_tenant()
    with pytest.raises(RuntimeError, match="unscoped database session"):
        async with isolated.get_tiered_db_session():
            pass
