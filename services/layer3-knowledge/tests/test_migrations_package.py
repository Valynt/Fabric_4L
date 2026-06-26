from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "migrations"


def test_migrations_directory_is_a_package() -> None:
    """Layer 3 migration docs use ``python -m migrations.<name>``; the directory
    must therefore contain an ``__init__.py``.
    """
    init_file = MIGRATIONS_DIR / "__init__.py"
    assert init_file.exists(), (
        "services/layer3-knowledge/src/migrations/__init__.py is missing; "
        "``python -m migrations.<name>`` will fail"
    )


def test_numbered_migration_module_is_importable() -> None:
    """Smoke-test that the 030 migration can be imported as a package module."""
    import importlib

    migration_030 = importlib.import_module(
        "migrations.030_neo4j_tenant_id_constraints_and_indexes"
    )

    assert hasattr(migration_030, "_main")
    assert hasattr(migration_030, "TenantIdConstraintMigration")
