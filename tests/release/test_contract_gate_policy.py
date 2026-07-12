"""Release Policy: Contract gate compliance.

Verifies that required contract gates exist and blocking gates do not use
continue-on-error that would allow violations to pass silently.
"""

import os
import re
from pathlib import Path

import jsonschema
import pytest
import yaml
from value_fabric.shared.audit.models import PolicyDecisionRecord


def _required_artifact_missing_message(path: Path, artifact_role: str) -> str:
    """Return a consistent fail-closed message for missing mandatory gate assets."""
    return (
        f"Required governance artifact missing: {path.as_posix()} "
        f"({artifact_role}). Release gate policy is fail-closed for mandatory assets."
    )


def _assert_required_artifact_exists(path: Path, artifact_role: str) -> None:
    """Fail closed when required release-governance assets are absent."""
    assert path.exists(), _required_artifact_missing_message(path, artifact_role)


class TestContractGatePolicy:
    """Enforce: Required contract gates exist; blocking gates don't use continue-on-error."""

    def test_structural_preflight_exists(self):
        """Required governance artifact: structural preflight must fail closed if absent."""
        script = Path("scripts/ci/structural_preflight.py")
        _assert_required_artifact_exists(
            script,
            "mandatory CI structural preflight script",
        )
        assert script.stat().st_size > 0, "structural_preflight.py is empty"

    def test_python_contract_lint_exists(self):
        """Required governance artifact: python contract lint must fail closed if absent."""
        script = Path("scripts/ci/python_contract_lint.py")
        _assert_required_artifact_exists(
            script,
            "mandatory CI contract lint script",
        )
        assert script.stat().st_size > 0, "python_contract_lint.py is empty"

    def test_ci_workflow_blocking_gates_no_continue_on_error(self):
        """Blocking gates in CI workflows must not use continue-on-error.

        continue-on-error: true allows failures to pass silently.
        Blocking gates must fail the build on violation.
        """
        workflows_dir = Path(".github/workflows")
        _assert_required_artifact_exists(
            workflows_dir,
            "mandatory GitHub Actions workflow directory for blocking gates",
        )

        violations = []
        for workflow_file in workflows_dir.glob("*.yml"):
            content = workflow_file.read_text(encoding="utf-8")

            # Check for continue-on-error in blocking gate contexts
            # This is a heuristic check - manual review may still be needed
            if "continue-on-error: true" in content:
                # Check if it's on a gate job (not upload/artifact steps)
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "continue-on-error: true" in line:
                        # Check surrounding context for gate-related patterns
                        context = "\n".join(lines[max(0, i-10):i+5])
                        gate_patterns = ["gate-", "security", "tenant", "boundary", "compliance", "lint"]
                        if any(pat in context.lower() for pat in gate_patterns):
                            violations.append(f"{workflow_file.name}: line {i+1}")

        if violations:
            details = "\n".join(f"  - {v}" for v in violations[:5])  # Limit output
            pytest.fail(
                f"Found potential continue-on-error in blocking gate contexts:\n{details}\n"
                f"Review these workflows to ensure blocking gates can actually fail."
            )

    def test_required_makefile_targets_exist(self):
        """Required governance artifact: Makefile gate targets must fail closed if absent."""
        makefile = Path("Makefile")
        _assert_required_artifact_exists(
            makefile,
            "mandatory root Makefile exposing release/security/contract gate targets",
        )

        content = makefile.read_text(encoding="utf-8")

        required_targets = [
            "gate-mandatory-security-regression",
            "gate-security",
            "gate-arch",
            "gate-state",
            "lint",
        ]

        missing = [t for t in required_targets if f"{t}:" not in content]

        if missing:
            pytest.fail(f"Required Makefile targets missing: {missing}")

    @pytest.mark.parametrize(
        ("path_str", "artifact_role"),
        [
            ("scripts/ci/structural_preflight.py", "mandatory CI structural preflight script"),
            ("scripts/ci/python_contract_lint.py", "mandatory CI contract lint script"),
            (".github/workflows", "mandatory GitHub Actions workflow directory for blocking gates"),
            ("Makefile", "mandatory root Makefile exposing release/security/contract gate targets"),
        ],
    )
    def test_required_gate_helper_fails_closed_for_missing_artifacts(self, tmp_path: Path, path_str: str, artifact_role: str):
        """Regression: required-gate helper must fail closed and emit standardized triage text."""
        missing_path = tmp_path / path_str
        with pytest.raises(AssertionError, match=r"^Required governance artifact missing: "):
            _assert_required_artifact_exists(missing_path, artifact_role)

    def test_mandatory_security_regression_gate_is_non_optional(self):
        """Sprint 2 mandatory security checks must be wired into gate-security.

        The production-readiness workflow invokes ``make gate-security`` for the
        security-isolation job. Making this aggregate gate a dependency of
        ``gate-security`` keeps the CI contract intact while ensuring auth,
        tenant-boundary, contract-drift, critical E2E guard, and workload
        hardening regressions cannot be skipped.
        """
        makefile = Path("Makefile")
        script = Path("scripts/ci/mandatory_security_regression_gate.sh")

        assert script.exists(), "mandatory security regression script is missing"
        assert script.stat().st_size > 0, "mandatory security regression script is empty"

        content = makefile.read_text(encoding="utf-8")
        assert "gate-security: gate-mandatory-security-regression" in content, (
            "gate-security must depend on gate-mandatory-security-regression so "
            "the existing production-readiness workflow cannot bypass it"
        )
        assert "bash scripts/ci/mandatory_security_regression_gate.sh" in content, (
            "Makefile target must invoke the canonical mandatory security regression script"
        )

    def test_policy_decision_record_schema_matches_shared_contract(self):
        """Sprint 3 runtime policy decisions must have explicit schema coverage."""
        schema_path = Path("packages/platform-contract/schemas/gate/policy-decision-record.schema.json")
        assert schema_path.exists(), "policy-decision detail schema is missing"
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))

        allowed = PolicyDecisionRecord(
            decision=True,
            reason="OPA allowed tool",
            obligations=["log_invocation"],
            policy_bundle_hash="a" * 64,
        ).model_dump()
        denied = PolicyDecisionRecord(
            decision=False,
            reason="invariant_blocked",
            obligations=["invariant_blocked"],
            policy_bundle_hash="b" * 64,
        ).model_dump()

        validator = jsonschema.Draft202012Validator(schema)
        validator.validate(allowed)
        validator.validate(denied)

    def test_backend_integrated_product_confidence_guard_is_structural(self):
        """Critical frontend journeys must fail closed and keep backend seeding wired."""
        guard = Path("apps/web/scripts/security/assert-no-skipped-critical-e2e.mjs")
        config = Path("apps/web/playwright.config.ts")
        crud = Path("apps/web/e2e/my-models.spec.ts")
        setup = Path("apps/web/e2e/global-setup.ts")
        package_json = Path("apps/web/package.json")

        assert guard.exists(), "critical E2E guard is missing"
        guard_text = guard.read_text(encoding="utf-8")
        config_text = config.read_text(encoding="utf-8")
        crud_text = crud.read_text(encoding="utf-8")
        setup_text = setup.read_text(encoding="utf-8")
        package_text = package_json.read_text(encoding="utf-8")

        assert "requiredEvidence" in guard_text, "guard must assert required backend wiring, not only skipped tests"
        assert "backend-integrated" in guard_text, "guard must protect the backend-integrated project"
        assert re.search(r"name:\s*['\"]backend-integrated['\"]", config_text)
        assert re.search(r"grep:\s*/@backend/", config_text)
        assert "globalSetup: './e2e/global-setup.ts'" in config_text
        assert "PLAYWRIGHT_BACKEND_URL is required for the @backend My Models CRUD journey" in crud_text
        assert "seed-e2e-data" in setup_text
        assert '"test:e2e:guard": "node scripts/security/assert-no-skipped-critical-e2e.mjs"' in package_text
        assert '"test:e2e:backend": "pnpm run test:e2e:guard && playwright test --project=backend-integrated"' in package_text

    def test_mandatory_security_regression_gate_covers_launch_blocker_surfaces(self):
        """Mandatory gate must cover the Sprint 2 launch-blocker surfaces."""
        script = Path("scripts/ci/mandatory_security_regression_gate.sh")
        if not script.exists():
            pytest.fail("mandatory security regression script is missing")

        content = script.read_text(encoding="utf-8")
        required_snippets = {
            "standalone_api_production_safety": "services/api",
            "i03_persistence_and_provider_boundary": "test_i03_durable_persistence_and_llm.py",
            "health_metrics_proof": "test_health.py",
            "tenant_boundary_security": "test_tenant_boundary_fails_closed.py",
            "cross_tenant_api_security": "test_cross_tenant_api.py",
            "cross_layer_tenant_matrix": "test_cross_layer_tenant_isolation_matrix.py",
            "shared_tenant_context_contract": "test_tenant_context_contract.py",
            "shared_import_boundary": "test_shared_import_boundary.py",
            "retention_deletion_contract": "test_retention_deletion_contract.py",
            "openapi_contract_drift": "contract-drift",
            "frontend_contract_placeholder_guard": "assert-no-placeholder-contract-tests.mjs",
            "critical_e2e_skip_guard": "assert-no-skipped-critical-e2e.mjs",
            "kubernetes_hardening": "tests/k8s/test_security_policies.py",
        }

        missing = [name for name, snippet in required_snippets.items() if snippet not in content]
        assert not missing, (
            "mandatory security regression gate is missing required launch-blocker surfaces: "
            f"{missing}"
        )

    def test_backend_integrated_validation_target_includes_direct_release_proofs(self):
        """Canonical backend-integrated gate must include the documented direct P0 proofs."""
        makefile = Path("Makefile").read_text(encoding="utf-8")
        target_start = makefile.index("test-backend-integrated-validation:")
        next_target = makefile.index("test-backend-integrated-release-smoke:", target_start)
        target_block = makefile[target_start:next_target]

        required_snippets = {
            "auth enforcement": "services/api/app/tests/test_auth_enforcement.py",
            "health proof": "services/api/app/tests/test_health.py",
            "durable persistence": "services/api/app/tests/test_i03_durable_persistence_and_llm.py",
            "production safety": "services/api/app/tests/test_production_safety.py",
            "retention deletion contract": "tests/contract/test_retention_deletion_contract.py",
            "backend integrated suite": "tests/backend_integrated -m backend_integrated -v",
        }

        missing = [name for name, snippet in required_snippets.items() if snippet not in target_block]
        assert not missing, (
            "test-backend-integrated-validation must include direct release proofs before "
            f"the live backend-integrated suite: {missing}"
        )
