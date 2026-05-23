from __future__ import annotations

import pytest

from app.core.database import InMemoryTable
from value_fabric.shared.database import MissingTenantContextError

# Valid UUID tenant IDs for tests that require UUID-format tenant context.
_TENANT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_TENANT_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def test_system_scope_requires_explicit_flag() -> None:
    """Passing tenant_id='system' alone must NOT return cross-tenant records.

    The reserved-keyword bypass requires allow_system_scope=True. Without it,
    'system' is treated as a literal tenant value — no records match, so the
    result is an empty list rather than a cross-tenant dump.
    """
    table: InMemoryTable = InMemoryTable("users", "tenant_id")
    table.insert("u-a", {"id": "u-a", "tenant_id": _TENANT_A, "email": "a@example.com"})
    table.insert("u-b", {"id": "u-b", "tenant_id": _TENANT_B, "email": "b@example.com"})

    # Without allow_system_scope, 'system' scopes to records owned by "system"
    # (none exist) — returns empty rather than leaking cross-tenant data.
    result = table.list(tenant_id="system")
    assert result == []


def test_system_scope_with_flag_returns_all_tenants() -> None:
    """allow_system_scope=True with a reserved keyword returns all records."""
    table: InMemoryTable = InMemoryTable("users", "tenant_id")
    table.insert("u-a", {"id": "u-a", "tenant_id": _TENANT_A, "email": "a@example.com"})
    table.insert("u-b", {"id": "u-b", "tenant_id": _TENANT_B, "email": "b@example.com"})

    results = table.list(tenant_id="system", allow_system_scope=True)
    ids = {r["id"] for r in results}
    assert ids == {"u-a", "u-b"}


def test_normal_tenant_list_scoped_correctly() -> None:
    """A normal UUID tenant_id only returns that tenant's records."""
    table: InMemoryTable = InMemoryTable("users", "tenant_id")
    table.insert("u-a", {"id": "u-a", "tenant_id": _TENANT_A, "email": "a@example.com"})
    table.insert("u-b", {"id": "u-b", "tenant_id": _TENANT_B, "email": "b@example.com"})

    results = table.list(tenant_id=_TENANT_A)
    assert len(results) == 1
    assert results[0]["id"] == "u-a"


def test_allow_system_scope_with_normal_tenant_still_scoped() -> None:
    """allow_system_scope=True with a non-reserved tenant_id still scopes normally."""
    table: InMemoryTable = InMemoryTable("users", "tenant_id")
    table.insert("u-a", {"id": "u-a", "tenant_id": _TENANT_A, "email": "a@example.com"})
    table.insert("u-b", {"id": "u-b", "tenant_id": _TENANT_B, "email": "b@example.com"})

    # allow_system_scope=True only widens scope when the keyword is reserved.
    results = table.list(tenant_id=_TENANT_A, allow_system_scope=True)
    assert len(results) == 1
    assert results[0]["id"] == "u-a"


def test_inmemory_table_denies_unscoped_reads_and_writes() -> None:
    table = InMemoryTable("accounts", "tenant_id")
    table.insert("acct-1", {"id": "acct-1", "tenant_id": "tenant-a", "name": "A"})

    with pytest.raises(MissingTenantContextError):
        table.get("acct-1")

    with pytest.raises(MissingTenantContextError):
        table.list()

    with pytest.raises(MissingTenantContextError):
        table.update("acct-1", name="updated")

    with pytest.raises(MissingTenantContextError):
        table.delete("acct-1")


def test_inmemory_table_requires_tenant_on_insert_and_scopes_results() -> None:
    table = InMemoryTable("accounts", "tenant_id")

    with pytest.raises(MissingTenantContextError):
        table.insert("acct-missing", {"id": "acct-missing", "name": "missing-tenant"})

    table.insert("acct-a", {"id": "acct-a", "tenant_id": "tenant-a", "name": "A"})
    table.insert("acct-b", {"id": "acct-b", "tenant_id": "tenant-b", "name": "B"})

    assert table.get("acct-a", tenant_id="tenant-a") == {
        "id": "acct-a",
        "tenant_id": "tenant-a",
        "name": "A",
    }
    assert table.get("acct-a", tenant_id="tenant-b") is None
    assert table.list(tenant_id="tenant-a") == [
        {"id": "acct-a", "tenant_id": "tenant-a", "name": "A"}
    ]


