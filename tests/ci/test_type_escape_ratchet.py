from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.ci import type_escape_ratchet

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_generated_python_sdk_is_excluded_from_type_escape_scan() -> None:
    generated_sdk_file = "sdk/python/src/valuefabric/generated/l4_client.py"

    assert type_escape_ratchet.matches_any(
        generated_sdk_file,
        type_escape_ratchet.EXCLUDED_PATTERNS,
    )


def test_scan_file_detects_supported_python_and_typescript_escapes(tmp_path: Path) -> None:
    python_file = tmp_path / "unsafe.py"
    typescript_file = tmp_path / "unsafe.ts"
    python_file.write_text("value: Any = source  # type: ignore[assignment]\n", encoding="utf-8")
    typescript_file.write_text("const value = source as any;\n", encoding="utf-8")

    python_kinds = {
        finding.kind for finding in type_escape_ratchet.scan_file(python_file, tmp_path)
    }
    typescript_kinds = {
        finding.kind for finding in type_escape_ratchet.scan_file(typescript_file, tmp_path)
    }

    assert python_kinds == {"python-any", "python-type-ignore"}
    assert typescript_kinds == {"typescript-as-any"}


def test_compare_occurrences_ignores_line_moves_but_blocks_added_duplicates() -> None:
    baseline = {
        "occurrences": [
            {
                "path": "sdk/client.py",
                "line": 10,
                "kind": "python-any",
                "text": "value: " + "A" + "ny",
            }
        ]
    }
    moved = type_escape_ratchet.Finding(
        path="sdk/client.py",
        line=20,
        kind="python-any",
        text="value: " + "A" + "ny",
    )

    new, stale = type_escape_ratchet.compare_occurrences([moved], baseline)
    assert new == []
    assert stale == 0

    new, stale = type_escape_ratchet.compare_occurrences([moved, moved], baseline)
    assert new == [moved]
    assert stale == 0


def test_type_escape_ratchet_has_public_local_entrypoints() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))

    assert "check-type-escape-ratchet:" in makefile
    assert package_json["scripts"]["check:type-escapes"] == "make check-type-escape-ratchet"


def test_structural_preflight_runs_type_escape_ratchet() -> None:
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/pr-checks.yml").read_text(encoding="utf-8")
    )

    commands = [step.get("run", "") for step in workflow["jobs"]["structural-preflight"]["steps"]]
    assert "make check-type-escape-ratchet" in commands
