"""Regression guard for unresolved git merge conflict blocks."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = REPO_ROOT / "scripts" / "ci" / "check_conflict_markers.py"
SPEC = importlib.util.spec_from_file_location("check_conflict_markers", CHECKER_PATH)
assert SPEC is not None and SPEC.loader is not None
check_conflict_markers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_conflict_markers)


def test_no_merge_conflict_markers_in_tracked_files() -> None:
    """The architecture guard must share the root conflict-marker contract."""

    tracked_files = check_conflict_markers._tracked_files(REPO_ROOT)
    conflicts = check_conflict_markers.find_conflicts(tracked_files)

    assert conflicts == []
