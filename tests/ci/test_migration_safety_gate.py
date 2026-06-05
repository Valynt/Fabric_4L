from __future__ import annotations

from pathlib import Path

from scripts.ci.check_migration_safety import _function_line_ranges, _requires_dry_run, scan


def test_function_line_ranges_identifies_upgrade_and_downgrade() -> None:
    lines = [
        "revision = '001'",
        "def upgrade() -> None:",
        "    pass",
        "",
        "def downgrade() -> None:",
        "    pass",
    ]

    assert _function_line_ranges(lines) == {"upgrade": (2, 4), "downgrade": (5, 6)}


def test_alembic_revision_does_not_require_dry_run_parameter() -> None:
    source = """
revision = "001"
down_revision = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
"""

    assert _requires_dry_run(source, Path("versions/001_example.py")) is False


def test_current_migration_safety_scan_has_no_findings() -> None:
    assert scan() == []
