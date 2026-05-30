"""Release-policy checks for destructive database migrations.

These tests intentionally inspect migration source because destructive schema
changes can pass application-level tests while still being unsafe to run against
production-like data. Any migration that drops tables, columns, or constraints
must document operator intent and include a fail-closed runtime guard.
"""

from __future__ import annotations

import re
from pathlib import Path


MIGRATION_ROOTS = [
    Path("services/layer1-ingestion/migrations/versions"),
    Path("services/layer2-extraction/migrations/versions"),
    Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
    Path("services/layer4-agents/migrations/versions"),
    Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
    Path("services/api/migrations/versions"),
]

DESTRUCTIVE_PATTERNS = (
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
    re.compile(r"\bdrop_table\s*\(", re.IGNORECASE),
    re.compile(r"\bdrop_column\s*\(", re.IGNORECASE),
)

REQUIRED_DESTRUCTIVE_MARKERS = (
    "DESTRUCTIVE",
    "backup",
    "data migration",
    "PRODUCTION_LIKE_ENVIRONMENTS",
    "DESTRUCTIVE_ACK_VALUE",
    "MIGRATION_",
    "RuntimeError",
)


def _migration_files() -> list[Path]:
    files: list[Path] = []
    for root in MIGRATION_ROOTS:
        if root.exists():
            files.extend(sorted(root.glob("*.py")))
    return files


def _upgrade_body(source: str) -> str:
    start = source.find("def upgrade")
    if start == -1:
        return ""
    end = source.find("def downgrade", start)
    return source[start:] if end == -1 else source[start:end]


def _downgrade_body(source: str) -> str:
    start = source.find("def downgrade")
    return "" if start == -1 else source[start:]


def _is_destructive(source: str) -> bool:
    return any(pattern.search(_upgrade_body(source)) for pattern in DESTRUCTIVE_PATTERNS)


class TestMigrationSafetyPolicy:

    def test_migration_roots_cover_all_alembic_managed_services_once(self) -> None:
        """Release policy must inspect each Alembic-managed PostgreSQL root exactly once."""
        expected = [
            Path("services/layer1-ingestion/migrations/versions"),
            Path("services/layer2-extraction/migrations/versions"),
            Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
            Path("services/layer4-agents/migrations/versions"),
            Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
            Path("services/api/migrations/versions"),
        ]

        assert MIGRATION_ROOTS == expected
        assert len(MIGRATION_ROOTS) == len(set(MIGRATION_ROOTS))
        missing = [root for root in MIGRATION_ROOTS if not root.exists()]
        assert not missing, f"Migration roots are missing: {missing}"

    def test_destructive_migrations_have_operator_acknowledgment_and_runtime_guard(self) -> None:
        """Destructive migrations must fail closed in production-like environments."""
        failures: list[str] = []
        destructive_seen = False

        for path in _migration_files():
            source = path.read_text(encoding="utf-8")
            if not _is_destructive(source):
                continue
            destructive_seen = True
            missing = [marker for marker in REQUIRED_DESTRUCTIVE_MARKERS if marker not in source]
            if missing:
                failures.append(f"{path}: missing {missing}")

        assert destructive_seen, "Expected at least one destructive migration so this policy remains exercised"
        assert not failures, "Unsafe destructive migration policy gaps: " + "; ".join(failures)

    def test_destructive_migrations_define_downgrade_path(self) -> None:
        """Release candidates must preserve rollback intent for destructive migrations."""
        failures: list[str] = []
        for path in _migration_files():
            source = path.read_text(encoding="utf-8")
            if not _is_destructive(source):
                continue
            downgrade = _downgrade_body(source)
            if not downgrade or re.search(r"def\s+downgrade\s*\([^)]*\)\s*->?[^:]*:\s*(pass|\.\.\.)\b", downgrade):
                failures.append(str(path))

        assert not failures, "Destructive migrations need non-empty downgrade paths: " + ", ".join(failures)

    def test_layer1_destructive_migration_guard_is_called_before_drop_operations(self) -> None:
        """The known Layer 1 destructive migration must guard before the first drop."""
        path = Path("services/layer1-ingestion/migrations/versions/003_spec_compliant_schema.py")
        source = path.read_text(encoding="utf-8")
        upgrade = _upgrade_body(source)
        guard_index = upgrade.find("_assert_legacy_tables_safe_to_drop()")
        first_drop_index = min(
            index for index in (upgrade.find("DROP TABLE"), upgrade.find("drop_index"), upgrade.find("drop_constraint")) if index != -1
        )
        assert guard_index != -1, "Layer 1 destructive migration is missing its fail-closed guard call"
        assert guard_index < first_drop_index, "Layer 1 destructive migration must guard before any drop operation"
