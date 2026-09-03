"""Contract tests for the CI-inputs / domain-inputs split in change scoping.

Enforces the P1 recovery objective that global CI changes must no longer
activate every layer/runtime scope, while allowlist-sensitive gates keep a
precise fail-open on exactly the gate inputs they read.

These tests are wired into structural-preflight (ungated) so the split ships
with live enforcement: a workflow-only or scripts-only PR resolves no domain
scope, and the heavy matrix is skipped only because those skips are provably
safe - never by accident.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PATHS_FILTERS = ROOT / ".github/paths-filters.yml"
CHANGE_SCOPE_ACTION = ROOT / ".github/actions/change-scope/action.yml"
PR_CHECKS = ROOT / ".github/workflows/pr-checks.yml"

BUNDLED_CI_PATHS = (".github/**", "scripts/**", "config/**", "Makefile", "pytest.ini")

# Scopes that must never bundle CI plumbing: changes to these paths cannot
# affect the domain surfaces those scopes represent.
DOMAIN_SCOPES = (
    "layer1",
    "layer2",
    "layer3",
    "layer4",
    "layer5",
    "layer6",
    "backend",
    "web",
    "k8s",
    "deps",
    "release-policy",
    "runtime",
)


def _paths() -> dict[str, list[str]]:
    return yaml.safe_load(PATHS_FILTERS.read_text(encoding="utf-8"))


def test_ci_input_scopes_are_first_class() -> None:
    data = _paths()
    for scope in ("ci-global", "ci-tooling", "ci-governance"):
        assert scope in data, f"missing CI-input scope {scope}"
    assert ".github/**" in data["ci-global"]
    assert "Makefile" in data["ci-global"]
    assert "scripts/**" in data["ci-tooling"]
    assert "config/**" in data["ci-governance"]
    assert "pytest.ini" in data["ci-governance"]


def test_domain_scopes_do_not_bundle_ci_plumbing() -> None:
    data = _paths()
    for scope in DOMAIN_SCOPES:
        patterns = data[scope]
        for bundled in BUNDLED_CI_PATHS:
            assert bundled not in patterns, (
                f"{scope} still bundles {bundled}; CI plumbing must live in the "
                "ci-global/ci-tooling/ci-governance scopes"
            )


def test_code_scope_keeps_precise_fail_open_on_security_gate_inputs() -> None:
    code = set(_paths()["code"])
    required_inputs = {
        ".semgrep/**",
        ".semgrepignore",
        "config/semgrep/**",
        "config/security/**",
        "config/ci/semgrep_baseline.json",
        "scripts/ci/check_semgrep_sarif.py",
    }
    missing = required_inputs - code
    assert not missing, f"code scope missing security gate inputs: {sorted(missing)}"


def test_docker_scope_keeps_precise_fail_open_on_trivy_policy() -> None:
    assert "config/trivy/**" in _paths()["docker"]


def test_code_scope_still_covers_all_runtime_security_surfaces() -> None:
    # Mirror of test_semgrep_behavioral_contracts' membership assertion so the
    # split cannot silently drop a runtime security surface from SAST.
    code = set(_paths()["code"])
    for surface in (
        "services/**",
        "apps/**",
        "packages/**",
        "contracts/**",
        "tests/**",
        "packs/**",
        "infra/**",
        "k8s/**",
        "sdk/**",
        "docs-site/**",
        "examples/**",
    ):
        assert surface in code, f"code scope dropped security surface {surface}"


def test_change_scope_action_emits_ci_input_scopes() -> None:
    action = CHANGE_SCOPE_ACTION.read_text(encoding="utf-8")
    for scope in ("ci-global", "ci-tooling", "ci-governance"):
        # outputs block entry (value from resolve step)
        assert f"value: ${{{{ steps.resolve.outputs.{scope} }}}}" in action
        # FILTER_* env passing: filter step must feed the resolve step
        env_name = f"FILTER_{scope.upper().replace('-', '_')}"
        assert f"{env_name}: ${{{{ steps.filter.outputs.{scope}_any_changed }}}}" in action
        # emit line: explicit 'false' is the only skip trigger; else fail open
        assert f"emit {scope} \"${{{env_name}}}\"" in action


def test_pr_checks_change_scope_exposes_ci_input_scopes() -> None:
    text = PR_CHECKS.read_text(encoding="utf-8")
    for scope in ("ci-global", "ci-tooling", "ci-governance"):
        assert f"{scope}: ${{{{ steps.scope.outputs.{scope} }}}}" in text, (
            f"pr-checks change-scope job missing output {scope}"
        )
        # Post-resolve: non-PR events (push/schedule) must force them true too,
        # otherwise they would stay empty and read as 'false' to consumers.
        assert f'echo "{scope}=true" >> $GITHUB_OUTPUT' in text, (
            f"pr-checks Post-resolve step missing {scope}=true"
        )
