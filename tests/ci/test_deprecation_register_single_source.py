"""D1 governance gate: one enforceable deprecation/compatibility source.

These tests lock in the convergence: runtime headers, service startup warnings,
and the CI gate must all read ``docs/deprecation_register.json`` through the
shared loader, and no runtime module may hardcode a sunset date.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTER = REPO_ROOT / "docs" / "deprecation_register.json"
SHARED_LOADER = (
    REPO_ROOT
    / "packages"
    / "shared"
    / "src"
    / "value_fabric"
    / "shared"
    / "governance"
    / "deprecation_register.py"
)
CI_GATE = REPO_ROOT / "scripts" / "ci" / "check_deprecations.py"
L1_MAIN = (
    REPO_ROOT
    / "services"
    / "layer1-ingestion"
    / "src"
    / "layer1_ingestion"
    / "api"
    / "main.py"
)
L1_COMPAT = (
    REPO_ROOT
    / "services"
    / "layer1-ingestion"
    / "src"
    / "layer1_ingestion"
    / "api"
    / "routes"
    / "compatibility.py"
)

_DATE_LITERAL = re.compile(r"['\"]20\d\d-\d\d-\d\d['\"]")


def test_canonical_loader_exists() -> None:
    assert SHARED_LOADER.is_file(), "the shared deprecation-register loader is missing"


def test_register_uses_items_schema() -> None:
    payload = json.loads(REGISTER.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert isinstance(payload["items"], list) and payload["items"]
    # The historical ``deprecations`` key produced a silently-empty register.
    assert "deprecations" not in payload


def test_every_register_item_carries_governance_fields() -> None:
    payload = json.loads(REGISTER.read_text(encoding="utf-8"))
    for item in payload["items"]:
        assert item.get("feature"), f"register item without feature: {item}"
        assert item.get("target_removal"), f"{item['feature']} has no target_removal"
        assert item.get("owner"), f"{item['feature']} has no owner"
        assert item.get("path"), f"{item['feature']} has no path"
        # An overdue entry is only acceptable with an explicit deferral rationale.
        if item.get("status") in {"deferred", "removed"}:
            assert item.get("rationale"), f"{item['feature']} needs a rationale"


@pytest.mark.parametrize("module", [L1_MAIN, L1_COMPAT], ids=["l1_main", "l1_compatibility"])
def test_layer1_modules_do_not_hardcode_sunset_dates(module: Path) -> None:
    source = module.read_text(encoding="utf-8")
    offenders = _DATE_LITERAL.findall(source)
    assert not offenders, (
        f"{module.relative_to(REPO_ROOT)} hardcodes date literal(s) {offenders}; "
        "register removal dates in docs/deprecation_register.json instead."
    )


def test_layer1_consumers_read_through_shared_loader() -> None:
    for module in (L1_MAIN, L1_COMPAT):
        source = module.read_text(encoding="utf-8")
        assert "value_fabric.shared.governance.deprecation_register" in source, (
            f"{module.relative_to(REPO_ROOT)} must consume the canonical loader"
        )


def test_ci_gate_reads_through_shared_loader() -> None:
    source = CI_GATE.read_text(encoding="utf-8")
    assert "value_fabric.shared.governance.deprecation_register" in source
    # The gate must not re-implement its own path resolution or schema.
    assert 'payload.get("items"' not in source


def test_shared_package_suite_runs_in_ci() -> None:
    """M3: the shared-package suite must be an executed CI signal."""
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "pr-checks.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["shared-and-tests-checks"]
    steps = job["steps"]
    run_bodies = "\n".join(step.get("run", "") for step in steps)

    assert "packages/shared/tests" in run_bodies, (
        "no CI step runs the shared-package suite; its failures would be invisible"
    )
    assert "collected zero tests" in run_bodies, (
        "the shared-package job must fail closed when zero tests are collected"
    )
