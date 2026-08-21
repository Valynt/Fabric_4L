"""Tests for check_scan_freshness.py."""

from __future__ import annotations

import time
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.ci.check_scan_freshness import (
    REQUIRED_LAYERS,
    verify_sarif_freshness,
    verify_workflow_schedules,
)


def test_verify_workflow_schedules() -> None:
    errors = verify_workflow_schedules()
    assert len(errors) == 0, f"Workflow schedule validation failed: {errors}"


def test_verify_sarif_freshness() -> None:
    with TemporaryDirectory() as tmpdir:
        sarif_file = Path(tmpdir) / "fresh.sarif"
        sarif_file.write_text("{}", encoding="utf-8")

        errors = verify_sarif_freshness([sarif_file], max_age_days=7)
        assert len(errors) == 0
