from __future__ import annotations

from pathlib import Path

import pytest

from value_fabric.shared.database.runtime_adapter import DatabaseAdapterConfig, RuntimeDatabaseAdapter


@pytest.mark.contract_static
def test_shared_adapter_accepts_postgresql_urls_in_production_mode() -> None:
    adapter = RuntimeDatabaseAdapter(
        DatabaseAdapterConfig(
            database_url="postgresql+asyncpg://app:pw@db.internal:5432/service",
            service_name="contract-test",
            production_mode=True,
        )
    )
    assert adapter.engine is not None


@pytest.mark.contract_static
def test_shared_adapter_rejects_sqlite_in_production_mode() -> None:
    with pytest.raises(RuntimeError, match="production runtime requires PostgreSQL"):
        RuntimeDatabaseAdapter(
            DatabaseAdapterConfig(
                database_url="sqlite+aiosqlite:///./test.db",
                service_name="contract-test",
                production_mode=True,
                allow_test_sqlite=True,
            )
        )


def _module_has_bypass_marker(path: Path) -> bool:
    return "INTENTIONAL_DB_ADAPTER_BYPASS = True" in path.read_text(encoding="utf-8")


@pytest.mark.contract_static
def test_intentional_local_db_modules_are_explicitly_marked() -> None:
    modules = [
        Path("services/layer1-ingestion/src/layer1_ingestion/shared/database.py"),
        Path("services/layer4-agents/src/database.py"),
        Path("services/layer5-ground-truth/src/layer5_ground_truth/database.py"),
    ]
    for module_path in modules:
        assert _module_has_bypass_marker(module_path), f"Missing bypass marker: {module_path}"
