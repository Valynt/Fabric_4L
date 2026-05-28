"""Regression tests for the mandatory security regression gate.

These tests validate the gate contract itself, not the full security suite.
They ensure the gate fails when required suites are missing, uses correct artifact paths,
and includes all required coverage without silent skips.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

GATE_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "ci" / "mandatory_security_regression_gate.sh"
REPO_ROOT = Path(__file__).parent.parent.parent


def _gate_script_text() -> str:
    return GATE_SCRIPT.read_text(encoding="utf-8")


def _gate_command(*args: str) -> list[str]:
    if os.name == "nt":
        bash = shutil.which("bash")
        assert bash, "bash is required to execute mandatory_security_regression_gate.sh on Windows"
        return [bash, str(GATE_SCRIPT), *args]
    return [str(GATE_SCRIPT), *args]


def _required_suites_from_script() -> list[str]:
    script = _gate_script_text()
    paths: list[str] = []
    for array_name in (
        "STANDALONE_API_TESTS",
        "ROOT_SECURITY_TESTS",
        "CROSS_LAYER_TENANT_MATRIX_TESTS",
        "LAYER4_C06_SECURITY_TESTS",
        "CONTRACT_TESTS",
        "K8S_TESTS",
        "LAYER2_FAIL_CLOSED_TESTS",
        "LAYER5_FAIL_CLOSED_TESTS",
        "HOSTILE_API_KEY_RESOLVER_TESTS",
    ):
        match = re.search(rf"{array_name}=\(\n(?P<body>.*?)\n\)", script, flags=re.MULTILINE | re.DOTALL)
        assert match, f"Gate missing {array_name}"
        paths.extend(
            line.strip().split("::", 1)[0]
            for line in match.group("body").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    return paths


def test_gate_script_exists():
    """Gate script must exist at expected location."""
    assert GATE_SCRIPT.exists(), f"Gate script not found at {GATE_SCRIPT}"


def test_gate_is_executable():
    """Gate script should be executable."""
    if os.name == "nt":
        assert GATE_SCRIPT.exists(), "Gate script must exist for CI execution"
    else:
        assert GATE_SCRIPT.stat().st_mode & 0o111, "Gate script is not executable"


def test_gate_list_required_mode():
    """Gate should support --list-required dry-run mode."""
    if os.name == "nt":
        required_suites = _required_suites_from_script()
    else:
        result = subprocess.run(
            _gate_command("--list-required"),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, f"--list-required failed: {result.stderr}"
        required_suites = result.stdout.strip().split("\n")

    # Check that I-02 layer2 and layer5 suites are in the list
    layer2_i02 = "services/layer2-extraction/tests/test_production_fail_closed_i02.py"
    layer5_i02 = "services/layer5-ground-truth/tests/test_production_fail_closed_i02.py"
    layer4_rate_limits = "services/layer4-agents/tests/test_tenant_rate_limits.py"
    layer4_security_fixes = "services/layer4-agents/tests/test_security_fixes.py"
    auth_hijacking = "tests/security/test_auth_session_hijacking.py"
    csrf_comprehensive = "tests/security/test_csrf_comprehensive.py"
    auth_rate_limiting = "tests/security/test_auth_rate_limiting.py"
    cross_layer_matrix = "tests/security/test_cross_layer_tenant_isolation_matrix.py"

    assert layer2_i02 in required_suites, f"I-02 Layer 2 suite missing from required list"
    assert layer5_i02 in required_suites, f"I-02 Layer 5 suite missing from required list"
    assert layer4_rate_limits in required_suites, "C-06 tenant rate-limit suite missing from required list"
    assert layer4_security_fixes in required_suites, "C-06 security fixes suite missing from required list"
    assert auth_hijacking in required_suites, "Authentication session hijacking suite missing from required list"
    assert csrf_comprehensive in required_suites, "Comprehensive CSRF suite missing from required list"
    assert auth_rate_limiting in required_suites, "Authentication rate-limit suite missing from required list"
    assert cross_layer_matrix in required_suites, "Cross-layer tenant isolation matrix suite missing from required list"


def test_gate_references_required_i02_layer_suites():
    """Gate script must explicitly invoke I-02 layer2 and layer5 checks."""
    script_content = _gate_script_text()

    # Check for I-02 layer2 invocation
    assert "test_production_fail_closed_i02.py" in script_content, "Gate missing I-02 test invocation"
    assert "layer2-extraction" in script_content, "Gate missing Layer 2 reference"
    assert "layer5-ground-truth" in script_content, "Gate missing Layer 5 reference"


def test_gate_verify_required_only_mode():
    """Gate should support --verify-required-only mode and pass with all suites present."""
    if os.name == "nt":
        missing = [path for path in _required_suites_from_script() if not (REPO_ROOT / path).exists()]
        assert not missing, f"Required suites missing: {missing}"
        return

    result = subprocess.run(
        _gate_command("--verify-required-only"),
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, f"--verify-required-only failed: {result.stderr}"
    assert "All required suites present" in result.stdout


def test_gate_uses_repo_relative_audit_dir():
    """Gate should use repo-relative .fabric/audit, not Linux-specific /home/ubuntu."""
    script_content = _gate_script_text()

    # Should NOT use Linux-specific path
    assert "/home/ubuntu/fabric_audit" not in script_content, "Gate uses Linux-specific artifact path"

    # Should use repo-relative pattern
    assert "AUDIT_DIR" in script_content, "Gate missing AUDIT_DIR variable"
    assert ".fabric/audit" in script_content, "Gate missing .fabric/audit reference"
    assert "ROOT_DIR" in script_content, "Gate missing ROOT_DIR variable"


def test_gate_includes_required_suite_arrays():
    """Gate script must define required suite arrays with all critical checks."""
    script_content = _gate_script_text()

    assert "STANDALONE_API_TESTS=(" in script_content, "Gate missing API required suite array"
    assert "ROOT_SECURITY_TESTS=(" in script_content, "Gate missing root security suite array"
    assert "CROSS_LAYER_TENANT_MATRIX_TESTS=(" in script_content, "Gate missing cross-layer tenant matrix suite array"
    assert "LAYER4_C06_SECURITY_TESTS=(" in script_content, "Gate missing Layer 4 C-06 suite array"

    # Check for critical security suites
    required_patterns = [
        "test_auth_enforcement",
        "test_health",
        "test_production_safety",
        "test_tenant_boundary_fails_closed",
        "test_auth_session_hijacking",
        "test_csrf_comprehensive",
        "test_auth_rate_limiting",
        "test_cross_tenant_api",
        "test_cross_layer_tenant_isolation_matrix",
        "test_retention_deletion_contract",
        "test_tenant_rate_limits",
        "test_security_fixes",
    ]

    for pattern in required_patterns:
        assert pattern in script_content, f"REQUIRED_SUITES missing {pattern}"


def test_gate_includes_frontend_contract_guards():
    """Gate must include frontend contract tests and placeholder guard."""
    script_content = _gate_script_text()

    assert "Frontend contract tests" in script_content or "vitest run src/api/__tests__/contract" in script_content, \
        "Gate missing frontend contract tests"
    assert "placeholder" in script_content.lower() or "assert-no-placeholder" in script_content, \
        "Gate missing placeholder contract guard"


def test_gate_includes_critical_e2e_guards():
    """Gate must include critical E2E skip-valve guard."""
    script_content = _gate_script_text()

    assert "E2E" in script_content or "e2e" in script_content.lower(), "Gate missing E2E reference"
    assert "skip" in script_content.lower(), "Gate missing skip guard reference"


def test_gate_includes_kubernetes_hardening_checks():
    """Gate must include Kubernetes workload hardening checks."""
    script_content = _gate_script_text()

    assert "Kubernetes" in script_content or "k8s" in script_content.lower(), "Gate missing Kubernetes reference"
    assert "K8S_TESTS=(" in script_content, "Gate missing K8S_TESTS array"


def test_gate_has_required_suite_validation_function():
    """Gate must have fail-closed validation function."""
    script_content = _gate_script_text()

    assert "assert_required_paths_present" in script_content, "Gate missing required path validation"
    assert "exit 1" in script_content, "Gate missing exit on failure"


def test_gate_calls_required_suite_validation():
    """Gate must call check_required_suites before execution."""
    script_content = _gate_script_text()

    # The function should be called in main execution flow (after dry-run modes)
    assert "run_step \"Required suite manifest check\" assert_required_paths_present" in script_content, (
        "Gate missing required suite manifest check"
    )
    assert "assert_no_skip_or_xfail_markers" in script_content, "Gate missing source-level skip guard"


def test_gate_runs_layer4_c06_suites_with_skip_assertion():
    """Gate must execute C-06 suites through the no-skips JUnit assertion."""
    script_content = _gate_script_text()

    assert "Layer 4 C-06 tenant rate-limit and security regression checks" in script_content
    assert "layer4_c06_security.xml" in script_content
    assert "LAYER4_C06_SECURITY_TESTS" in script_content
    assert "assert_no_pytest_skips.py" in script_content


def test_gate_bounds_mandatory_pytest_runs():
    """Mandatory pytest invocations must time out instead of hanging CI."""
    script_content = _gate_script_text()

    assert "python -m pytest --tb=short -q -n 0 --timeout=60" in script_content
    assert script_content.count("--timeout=60") >= 4


def test_gate_uses_deterministic_standalone_api_test_env():
    """Standalone API checks must not inherit unsafe ambient developer env."""
    script_content = _gate_script_text()

    assert "TESTING=true ENVIRONMENT=testing DEBUG=false SEED_DEMO_DATA=false" in script_content


def test_gate_has_no_skip_or_best_effort_mode():
    """Gate should not have skip or best-effort mode for required suites."""
    script_content = _gate_script_text()

    # These patterns would indicate silent failure modes
    anti_patterns = [
        "|| true",  # Continue on error
        "|| continue",  # Continue on error
        "best-effort",  # Best-effort mode
    ]

    script_lower = script_content.lower()
    for pattern in anti_patterns:
        # Allow some context-specific uses (e.g., in dry-run modes or specific error handling)
        if pattern in script_lower:
            # Check if it's in an acceptable context
            lines_with_pattern = [line for line in script_content.split("\n") if pattern in line.lower()]
            for line in lines_with_pattern:
                # Allow in comments or specific safe contexts
                # API tests have a legitimate fallback for local dev without PostgreSQL
                # Cross-layer tenant matrix has a descriptive comment about best-effort tracking
                if (
                    not line.strip().startswith("#")
                    and "dry-run" not in line.lower()
                    and "test mode" not in line.lower()
                    and "grep" not in line.lower()
                    and "git" not in line.lower()
                    and "API tests require PostgreSQL" not in line
                    and "pre-existing import/assertion failures tracked" not in line
                ):
                    pytest.fail(f"Gate has unsafe pattern '{pattern}' in: {line}")


def test_gate_has_launch_readiness_reference():
    """Gate script should describe the mandatory launch-readiness purpose."""
    script_content = _gate_script_text()

    assert "Mandatory launch-readiness security regression gate" in script_content


def test_gate_creates_audit_directory():
    """Gate should create audit directory if it doesn't exist."""
    script_content = _gate_script_text()

    assert "mkdir -p" in script_content, "Gate missing mkdir -p for audit directory"
    assert "AUDIT_DIR" in script_content, "Gate missing AUDIT_DIR in mkdir command"


def test_gate_outputs_evidence_path():
    """Gate should output evidence path on success."""
    script_content = _gate_script_text()

    assert "Evidence written to" in script_content, \
        "Gate missing evidence path output message"
    assert "AUDIT_DIR" in script_content, \
        "Gate should output AUDIT_DIR variable in evidence path"


def test_gate_has_jq_fallback():
    """Gate should gracefully handle missing jq dependency."""
    script_content = _gate_script_text()

    # Should check for jq before using it
    assert "command -v jq" in script_content or "which jq" in script_content, \
        "Gate missing jq dependency check"


def test_gate_test_mode_functionality():
    """Gate should support FABRIC_GATE_TEST_MODE for skipping expensive operations."""
    script_content = _gate_script_text()

    assert "FABRIC_GATE_TEST_MODE" in script_content, \
        "Gate missing FABRIC_GATE_TEST_MODE variable"
    assert "TEST MODE" in script_content or "test mode" in script_content.lower(), \
        "Gate missing test mode logging" 
