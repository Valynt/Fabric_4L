from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
PR_WORKFLOWS = (
    ROOT / ".github/workflows/pr-checks.yml",
    ROOT / ".depot/workflows/pr-checks.yml",
)

HEALTH_RATCHET_LEAVES = {
    "check-conflict-markers",
    "check-no-nul-bytes",
    "check-type-escape-ratchet",
    "check-structural-fitness-ratchet",
    "check-dead-code",
    "check-legacy-debt",
    "check-operational-debt",
    "check-behavior-contract",
    "check-compatibility-shims",
    "check-temporal-skips",
    "check-test-skip-register-uniqueness",
    "check-reports-evidence-policy",
    "check-migration-entrypoints",
    "check-migration-rollback-policy",
    "check-migration-runtime-consistency",
    "check-risk-register",
}


def _logical_assignment(source: str, name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}\s*:=\s*(.*(?:\\\n\s*.*)*)$",
        source,
        re.MULTILINE,
    )
    assert match is not None, f"missing Make assignment {name}"
    return match.group(1).replace("\\\n", " ")


def _target_prerequisites(source: str, target: str) -> list[str]:
    match = re.search(rf"^{re.escape(target)}:\s*(.*?)\s*##", source, re.MULTILINE)
    assert match is not None, f"missing public target {target}"
    return match.group(1).split()


def test_pr_workflows_use_only_the_health_ratchet_aggregate() -> None:
    for workflow in PR_WORKFLOWS:
        source = workflow.read_text(encoding="utf-8")
        assert source.count("make check-health-ratchets") == 1, workflow
        for leaf in HEALTH_RATCHET_LEAVES:
            assert f"make {leaf}" not in source, f"{workflow}: direct leaf {leaf}"


def test_verify_uses_aggregate_instead_of_enumerating_leaves() -> None:
    source = MAKEFILE.read_text(encoding="utf-8")
    verify_checks = set(_logical_assignment(source, "VERIFY_CHECKS").split())
    assert "check-health-ratchets" in verify_checks
    assert not HEALTH_RATCHET_LEAVES.intersection(verify_checks)


def test_health_aggregate_has_one_migration_implementation() -> None:
    source = MAKEFILE.read_text(encoding="utf-8")
    prerequisites = _target_prerequisites(source, "check-health-ratchets")
    assert set(prerequisites) == HEALTH_RATCHET_LEAVES
    assert "check-migration-heads" not in prerequisites

    heads = _target_prerequisites(source, "check-migration-heads")
    assert heads == ["check-migration-entrypoints"]
    assert source.count("scripts/ci/check_migration_entrypoints.py") == 1
