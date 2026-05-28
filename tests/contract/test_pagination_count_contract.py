"""Contract tests for pagination count performance (P1-016).

Ensures InMemoryTable.count() returns correct totals without fetching all rows,
and that paginated API gateway endpoints use count() rather than len(list()).
"""

from __future__ import annotations

import pytest


try:
    import fastapi  # noqa: F401
    _SERVICE_DEPS_AVAILABLE = True
except ImportError:
    _SERVICE_DEPS_AVAILABLE = False

_skip_no_service_deps = pytest.mark.skipif(
    not _SERVICE_DEPS_AVAILABLE,
    reason="service runtime deps (fastapi, pydantic, etc.) not installed",
)


@pytest.mark.contract_static_no_service
@_skip_no_service_deps
def test_inmemory_table_count_parity_without_filter() -> None:
    """count() must match len(list()) for tenant-scoped queries."""
    from app.core.database import InMemoryTable

    table: InMemoryTable[dict] = InMemoryTable("test", "tenant_id")
    t1 = "11111111-1111-1111-1111-111111111111"
    t2 = "22222222-2222-2222-2222-222222222222"
    for i in range(5):
        table.insert(f"id-{i}", {"tenant_id": t1, "val": i})
    for i in range(3):
        table.insert(f"id-t2-{i}", {"tenant_id": t2, "val": i})

    assert table.count(tenant_id=t1) == 5
    assert table.count(tenant_id=t2) == 3
    assert table.count(tenant_id=t1) == len(table.list(tenant_id=t1))
    assert table.count(tenant_id=t2) == len(table.list(tenant_id=t2))


@pytest.mark.contract_static_no_service
@_skip_no_service_deps
def test_inmemory_table_count_parity_with_filter() -> None:
    """count() with filter_fn must match len(list()) with the same filter."""
    from app.core.database import InMemoryTable

    table: InMemoryTable[dict] = InMemoryTable("test", "tenant_id")
    t1 = "11111111-1111-1111-1111-111111111111"
    for i in range(10):
        table.insert(f"id-{i}", {"tenant_id": t1, "account_id": "a1" if i % 2 == 0 else "a2"})

    filter_a1 = lambda d: d["account_id"] == "a1"  # noqa: E731
    assert table.count(tenant_id=t1, filter_fn=filter_a1) == 5
    assert table.count(tenant_id=t1, filter_fn=filter_a1) == len(
        table.list(tenant_id=t1, filter_fn=filter_a1)
    )


@pytest.mark.contract_static_no_service
@_skip_no_service_deps
def test_inmemory_table_count_returns_int_not_list() -> None:
    """count() must return an int, never a list, to avoid O(n) memory fetch."""
    from app.core.database import InMemoryTable

    table: InMemoryTable[dict] = InMemoryTable("test", "tenant_id")
    t1 = "11111111-1111-1111-1111-111111111111"
    table.insert("id-1", {"tenant_id": t1})

    result = table.count(tenant_id=t1)
    assert isinstance(result, int)
    assert result == 1


@pytest.mark.contract_static_no_service
@_skip_no_service_deps
def test_async_inmemory_table_count_parity() -> None:
    """AsyncInMemoryTable.count() must match AsyncInMemoryTable.list() length."""
    import asyncio
    from app.core.database import AsyncInMemoryTable

    table: AsyncInMemoryTable[dict] = AsyncInMemoryTable("test", "tenant_id")
    t1 = "11111111-1111-1111-1111-111111111111"
    for i in range(4):
        asyncio.get_event_loop().run_until_complete(
            table.insert(f"id-{i}", {"tenant_id": t1, "account_id": "a1" if i < 2 else "a2"})
        )

    filter_a1 = lambda d: d["account_id"] == "a1"  # noqa: E731
    count_result = asyncio.get_event_loop().run_until_complete(
        table.count(tenant_id=t1, filter_fn=filter_a1)
    )
    list_result = asyncio.get_event_loop().run_until_complete(
        table.list(tenant_id=t1, filter_fn=filter_a1)
    )
    assert count_result == len(list_result)
    assert count_result == 2


@pytest.mark.contract_static_no_service
@_skip_no_service_deps
def test_paginated_endpoints_use_count_not_len_list() -> None:
    """Static check: no router may compute total via len(db.<table>.list(...))."""
    import ast
    from pathlib import Path

    routers_dir = Path(__file__).resolve().parents[2] / "services" / "api" / "app" / "routers"
    violations: list[str] = []
    for py_file in routers_dir.glob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        if "len(db." in source and ".list(" in source:
            # Precise check: does any line contain both len(db. and .list(
            for lineno, line in enumerate(source.splitlines(), start=1):
                if "len(db." in line and ".list(" in line:
                    violations.append(f"{py_file.name}:{lineno}")

    assert not violations, (
        f"Paginated endpoints must use count() instead of len(list()): {violations}"
    )
