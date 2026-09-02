from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci.generate_make_task_inventory import InventoryError, build_inventory, main


ROOT = Path(__file__).resolve().parents[2]


VALID_MAKEFILE = """\
.PHONY: public alias internal

public: dependency | order-only ## Public command
\t@echo public
\t@echo complete

alias: public ## Compatibility alias

internal:
\t@echo internal

.ONESHELL:
VALUE := not-a-target
"""


def _write_makefile(tmp_path: Path, text: str = VALID_MAKEFILE) -> Path:
    makefile = tmp_path / "Makefile"
    makefile.write_text(text, encoding="utf-8")
    return makefile


def test_build_inventory_is_deterministic_and_complete(tmp_path: Path) -> None:
    makefile = _write_makefile(tmp_path)

    inventory = build_inventory(makefile)

    assert inventory["metadata"] == {
        "internal_target_count": 1,
        "phony_target_count": 3,
        "public_target_count": 2,
        "schema_version": 1,
        "source": "Makefile",
        "source_sha256": "b2d22a526b3a6134d64642a394fe9330490b8cb7cf48a52667c91b971d781704",
        "target_count": 3,
    }
    assert inventory["targets"] == [
        {
            "artifacts": "undeclared",
            "cache_policy": "disabled",
            "description": "Compatibility alias",
            "environment_inputs": "ambient-unbounded",
            "implementation": "dependency-only",
            "line": 7,
            "lifecycle": "active",
            "name": "alias",
            "owner": "make",
            "owners": ["@value-fabric/sre-leads", "@value-fabric/maintainers"],
            "phony": True,
            "portability": "posix-bash",
            "prerequisites": ["public"],
            "public": True,
            "recipe_line_count": 0,
            "recipe_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "side_effects": "unbounded",
            "visibility": "public",
        },
        {
            "artifacts": "undeclared",
            "cache_policy": "disabled",
            "description": "",
            "environment_inputs": "ambient-unbounded",
            "implementation": "native",
            "line": 9,
            "lifecycle": "internal",
            "name": "internal",
            "owner": "make",
            "owners": ["@value-fabric/sre-leads", "@value-fabric/maintainers"],
            "phony": True,
            "portability": "posix-bash",
            "prerequisites": [],
            "public": False,
            "recipe_line_count": 1,
            "recipe_sha256": "253e4bcca5fa653e7b211324f1fd32d75fd08516deac3122eb7822c01884bef0",
            "side_effects": "unbounded",
            "visibility": "internal",
        },
        {
            "artifacts": "undeclared",
            "cache_policy": "disabled",
            "description": "Public command",
            "environment_inputs": "ambient-unbounded",
            "implementation": "native",
            "line": 3,
            "lifecycle": "active",
            "name": "public",
            "owner": "make",
            "owners": ["@value-fabric/sre-leads", "@value-fabric/maintainers"],
            "phony": True,
            "portability": "posix-bash",
            "prerequisites": ["dependency", "order-only"],
            "public": True,
            "recipe_line_count": 2,
            "recipe_sha256": "975c51dbb2b00c957b3a0f4024e1131b028b1637cc57b9628e0f9a62689f36d1",
            "side_effects": "unbounded",
            "visibility": "public",
        },
    ]


@pytest.mark.parametrize(
    ("makefile_text", "error"),
    [
        (
            ".PHONY: task\n.PHONY: task\ntask: ## Task\n\t@true\n",
            "duplicate .PHONY declarations: task",
        ),
        (
            ".PHONY: task\ntask: ## Task\n\t@true\ntask: other\n",
            "duplicate target definitions: task",
        ),
        (
            ".PHONY: missing\ntask:\n\t@true\n",
            ".PHONY names without target definitions: missing",
        ),
        (
            "task: ## Public task\n\t@true\n",
            "targets missing .PHONY: task",
        ),
    ],
)
def test_build_inventory_rejects_ambiguous_contracts(
    tmp_path: Path, makefile_text: str, error: str
) -> None:
    makefile = _write_makefile(tmp_path, makefile_text)

    with pytest.raises(InventoryError, match=error.replace(".", r"\.")):
        build_inventory(makefile)


def test_cli_write_then_default_check_and_detect_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    makefile = _write_makefile(tmp_path)
    output = tmp_path / "inventory.json"

    assert main(["--makefile", str(makefile), "--output", str(output), "--write"]) == 0
    assert main(["--makefile", str(makefile), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["metadata"]["target_count"] == 3

    output.write_text("{}\n", encoding="utf-8")
    assert main(["--makefile", str(makefile), "--output", str(output), "--check"]) == 1
    assert "task inventory is stale" in capsys.readouterr().err


def test_repository_inventory_is_current_and_complete() -> None:
    inventory = build_inventory(ROOT / "Makefile")
    checked_in = json.loads(
        (ROOT / "config/ci/make-task-inventory.json").read_text(encoding="utf-8")
    )

    assert inventory == checked_in
    metadata = inventory["metadata"]
    assert metadata["internal_target_count"] == 3
    assert metadata["phony_target_count"] == 236
    assert metadata["public_target_count"] == 233
    assert metadata["target_count"] == 236
    assert all(target["phony"] for target in inventory["targets"])
    assert all(target["cache_policy"] == "disabled" for target in inventory["targets"])
