from __future__ import annotations

from pathlib import Path

import yaml
from scripts.ci.check_test_skip_register_uniqueness import find_duplicates


def _write_register(path: Path, entries: list[dict[str, str]]) -> None:
    path.write_text(yaml.safe_dump({"entries": entries}, sort_keys=False), encoding="utf-8")


def test_duplicate_uniqueness_key_is_reported(tmp_path: Path) -> None:
    register = tmp_path / "register.yaml"
    _write_register(
        register,
        [
            {
                "id": "skip-001",
                "path_pattern": "tests/security/test_auth.py",
                "marker": "pytest.skip",
                "reason_pattern": "dependency missing",
            },
            {
                "id": "skip-002",
                "path_pattern": "tests/security/test_auth.py",
                "marker": "pytest.skip",
                "reason_pattern": "dependency missing",
            },
        ],
    )

    duplicates = find_duplicates(register)
    assert len(duplicates) == 1
    assert duplicates[("tests/security/test_auth.py", "pytest.skip", "dependency missing")] == [
        (1, "skip-001"),
        (2, "skip-002"),
    ]


def test_distinct_reason_pattern_is_not_duplicate(tmp_path: Path) -> None:
    register = tmp_path / "register.yaml"
    _write_register(
        register,
        [
            {
                "id": "skip-001",
                "path_pattern": "tests/security/test_auth.py",
                "marker": "pytest.skip",
                "reason_pattern": "dependency missing",
            },
            {
                "id": "skip-002",
                "path_pattern": "tests/security/test_auth.py",
                "marker": "pytest.skip",
                "reason_pattern": "upstream service unavailable",
            },
        ],
    )

    assert find_duplicates(register) == {}
