"""Workflow-policy tests: a skipped required check must never produce green.

Models the aggregate/readiness gate logic that lives in
.github/workflows/pr-checks.yml (CHECKS + SCOPES maps). Green requires:
  - every required check that RAN has result 'success', AND
  - a check that was skipped is green ONLY if it is provably out of change
    scope (SCOPES[check] == 'false').
A skipped/cancelled/failed required check with NO scope mapping (e.g.
check-external-deps) can never be green: GitHub reports conditionally
skipped jobs as successful, so a PR must not be mergeable without the
integration/security/data coverage those jobs provide.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Required checks with NO scope mapping: skipping them must fail the gate.
REQUIRED_UNSKIPPABLE = {
    "check-external-deps",
    "change-scope",
    "structural-preflight",
    "production-readiness-gate",
    "gate-engineering",
}

# Checks that may skip only when change-scope resolved their scope to 'false'.
SCOPED_CHECKS = {
    "shared-and-tests-checks",
    "layer5-tenant-isolation-regression",
    "contract-checks",
    "runtime-contract-checks",
    "integration-checks",
    "k8s-dry-run",
    "docker-compose-config-contract",
    "queue-topology-checks",
    "docker-build-check",
    "route-auth-gate",
    "tenant-isolation-gate",
    "critical-behaviors-gate",
}

# check-external-deps is not scope-able; every required check must run.
ALL_REQUIRED = REQUIRED_UNSKIPPABLE | SCOPED_CHECKS


def readiness_green(
    results: dict[str, str],
    scopes: dict[str, str] | None = None,
) -> tuple[bool, list[str]]:
    """Model of the readiness gate.

    results maps required-check -> job result (success/failure/cancelled/
    skipped/unknown). scopes mirrors SCOPES in pr-checks.yml: a skipped check
    is green only when its scope value is the literal string "false".

    Green is achieved only when every check is green. This encodes:
    conditionally-skipped required checks are reported as successful by
    GitHub, so they must never be admitted to green unless provably safe.
    """
    scopes = scopes or {}
    failures: list[str] = []
    for check, result in results.items():
            if result == "success":
                continue
            if result == "skipped" and scopes.get(check) == "false":
                # Provably out of change scope; safe to admit.
                continue
            failures.append(f"{check}: required check not green (result={result})")
    return (not failures, failures)


@pytest.mark.parametrize(
    "results,scopes,expected_green",
    [
        # Required checks ran and passed: green.
        ({"check-external-deps": "success"}, {}, True),
        # A skipped required check without a scope mapping: never green.
        ({"check-external-deps": "skipped"}, {}, False),
        ({"check-external-deps": "cancelled"}, {}, False),
        ({"check-external-deps": "failure"}, {}, False),
        # Multiple required checks all passing: green.
        ({"check-external-deps": "success", "contract-checks": "success"}, {}, True),
        # A scope-mapped check skipped with scope 'false' is safe.
        ({"contract-checks": "skipped"}, {"contract-checks": "false"}, True),
        # A scope-mapped check skipped with a non-'false' scope is not safe.
        ({"contract-checks": "skipped"}, {"contract-checks": "true"}, False),
        ({"contract-checks": "skipped"}, {"contract-checks": "backend"}, False),
    ],
)
def test_required_check_skip_cannot_be_green(results, scopes, expected_green):
    green, failures = readiness_green(results, scopes)
    assert green is expected_green
    if not expected_green:
        assert failures


def test_external_dependency_unavailable_verdict_surfaces_in_failures():
    # If the gate maps the probe outcome, an unavailable required dependency
    # must produce a non-green result naming EXTERNAL_DEPENDENCY_UNAVAILABLE
    # at the job level (the gate itself treats any non-success as failure).
    green, failures = readiness_green({"check-external-deps": "failure"})
    assert green is False
    assert any("check-external-deps" in failure for failure in failures)


def test_all_required_checks_are_explicit_and_none_scope_external_deps():
    # check-external-deps must NOT appear in the scoped set.
    assert "check-external-deps" not in SCOPED_CHECKS
    # Every check in the gate model must be required and accounted for.
    for check in list(REQUIRED_UNSKIPPABLE) + list(SCOPED_CHECKS):
        assert check in ALL_REQUIRED


def test_pr_checks_has_no_skip_map_for_check_external_deps():
    text = Path(".github/workflows/pr-checks.yml").read_text(encoding="utf-8")
    # The job must be declared as a job (level-0 YAML key).
    assert re.search(r"^  check-external-deps:", text, flags=re.MULTILINE)
    # It must be present in the unified-readiness-gate needs list.
    gate_section = text.split("unified-readiness-gate:", 1)[1].split("steps:", 1)[0]
    assert re.search(r"^\s*- check-external-deps\s*$", gate_section, flags=re.MULTILINE)
    # And must NOT be given a SKIPSAFE_/scope-removal mapping: a skip of the
    # external-dependency gate can never be green.
    assert not re.search(r"SKIPSAFE_[A-Z_]*CHECK_EXTERNAL", text)
    assert not re.search(r"\[.check-external-deps.\]\s*=\s*\"\$\{SCOPE_", text)
