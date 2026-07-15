from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "classify_failure.py"
GOVERNANCE_CATEGORIES = {
    "infra/setup",
    "dependency/cache",
    "flaky test",
    "real regression",
    "contract drift",
    "lint/type debt",
    "environment/secret issue",
}


def _load_module():
    spec = importlib.util.spec_from_file_location("classify_failure", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_classifier_detects_governance_taxonomy_categories() -> None:
    module = _load_module()
    classifier = module.FailureClassifier()
    cases = {
        "actions/setup-node@v4 failed: unable to resolve action during tool bootstrap": "infra/setup",
        "pnpm install --frozen-lockfile failed after actions/cache reported cache corrupt": "dependency/cache",
        "pip wheel unavailable: cache restore failed and No matching distribution found": "dependency/cache",
        "Playwright TimeoutError after 30000ms; same commit passed on rerun without code changes": "flaky test",
        "tenant isolation regression: tenant_id mismatch allowed cross-tenant access": "real regression",
        "OpenAPI contract drift: response shape required field missing from generated DTOs": "contract drift",
        "ruff check failed with F401; mypy reported [attr-defined]; ESLint no-explicit-any": "lint/type debt",
        "Infisical missing secret: OIDC credentials not configured for AWS_ROLE_ARN": "environment/secret issue",
    }

    for output, expected in cases.items():
        result = classifier.classify(output)
        assert result.category_key == expected
        assert result.category_key in GOVERNANCE_CATEGORIES


def test_launch_readiness_labels_are_secondary_metadata() -> None:
    module = _load_module()
    classifier = module.FailureClassifier()

    result = classifier.classify("OpenAPI contract drift: response shape required field missing")

    assert result.category_key == "contract drift"
    assert result.secondary_category_key == "CONTRACT_BOUNDARY_DRIFT"
    assert result.secondary_category_name == "Contract Boundary Drift"


def test_every_result_uses_governance_category_even_for_unknown_text() -> None:
    module = _load_module()
    classifier = module.FailureClassifier()

    for output in (
        "tenant isolation failed for JWT auth",
        "missing secret for external service",
        "operation timed out after 60s",
        "unclassified opaque failure text",
    ):
        result = classifier.classify(output)
        assert result.category_key in GOVERNANCE_CATEGORIES
        assert result.secondary_category_key or result.category_key != "real regression"


def test_cli_outputs_stable_json_and_blocks_on_blocker(tmp_path: Path) -> None:
    log = tmp_path / "failure.log"
    log.write_text("OpenAPI contract drift: response shape required field missing\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(log), "--format", "json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload[0]["category_key"] == "contract drift"
    assert payload[0]["secondary_category_key"] == "CONTRACT_BOUNDARY_DRIFT"
    assert payload[0]["blocks_ga"] is True
    assert payload[0]["fix_strategy"] == "align_contract_boundary"


def test_cli_non_blocker_returns_zero(tmp_path: Path) -> None:
    log = tmp_path / "failure.log"
    log.write_text(
        "Playwright TimeoutError after 30000ms; rerun passed without code changes\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(log), "--format", "markdown"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "flaky test" in result.stdout
    assert "TIMEOUT" in result.stdout
