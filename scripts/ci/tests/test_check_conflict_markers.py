from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "check_conflict_markers.py"
SPEC = importlib.util.spec_from_file_location("check_conflict_markers", MODULE_PATH)
check_conflict_markers = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_conflict_markers)


def test_conflict_marker_checker_rejects_complete_conflict_block(tmp_path: Path) -> None:
    conflicted = tmp_path / "conflicted.py"
    conflicted.write_text(
        "<<<<<<< HEAD\nleft\n=======\nright\n>>>>>>> branch\n",
        encoding="utf-8",
    )

    assert check_conflict_markers.main([str(conflicted)]) == 1


def test_conflict_marker_checker_allows_section_dividers(tmp_path: Path) -> None:
    clean = tmp_path / "clean.md"
    clean.write_text(
        "# Notes\n\n=======\n\nThis is a Markdown divider, not a conflict block.\n",
        encoding="utf-8",
    )

    assert check_conflict_markers.main([str(clean)]) == 0
