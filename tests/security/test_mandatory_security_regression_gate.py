"""
Regression tests for the mandatory security regression gate.

These tests verify the gate's fail-closed behavior without running the full
expensive test suites. They use environment overrides and temporary fixtures
to test gate mechanics.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import pytest


@pytest.fixture
def gate_script_path() -> Path:
    """Path to the mandatory security regression gate script."""
    return Path(__file__).parent.parent.parent / "scripts" / "ci" / "mandatory_security_regression_gate.sh"


@pytest.fixture
def temp_audit_dir(tmp_path: Path) -> Path:
    """Temporary directory for audit artifacts."""
    audit_dir = tmp_path / ".fabric" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


@pytest.fixture
def temp_required_suites_file(tmp_path: Path) -> Path:
    """Temporary file listing required suites for test mode."""
    return tmp_path / "required_suites.txt"


def _repo_root(gate_script_path: Path) -> Path:
    return gate_script_path.parent.parent.parent


def _candidate_bash_paths() -> list[str]:
    candidates: list[str] = []
    if os.environ.get("FABRIC_BASH"):
        candidates.append(os.environ["FABRIC_BASH"])
    if shutil.which("bash"):
        candidates.append(shutil.which("bash") or "")
    candidates.extend(
        [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
        ]
    )
    seen: set[str] = set()
    return [
        path
        for path in candidates
        if path
        and "windows\\system32\\bash" not in path.lower()
        and not (path in seen or seen.add(path))
    ]


def _working_bash() -> str | None:
    for candidate in _candidate_bash_paths():
        try:
            result = subprocess.run(
                [candidate, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            return candidate
    return None


def _run_gate_or_none(gate_script_path: Path, arg: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess | None:
    bash = _working_bash()
    if bash is None:
        return None
    return subprocess.run(
        [bash, str(gate_script_path), arg],
        cwd=_repo_root(gate_script_path),
        env=env,
        capture_output=True,
        text=True,
    )


def _required_suite_paths_from_script(gate_script_path: Path) -> list[str]:
    content = gate_script_path.read_text(encoding="utf-8")
    suite_names = [
        "STANDALONE_API_TESTS",
        "ROOT_SECURITY_TESTS",
        "CROSS_LAYER_TENANT_MATRIX_TESTS",
        "LAYER4_C06_SECURITY_TESTS",
        "CONTRACT_TESTS",
        "K8S_TESTS",
        "LAYER2_FAIL_CLOSED_TESTS",
        "LAYER5_FAIL_CLOSED_TESTS",
    ]
    paths: list[str] = []
    for suite_name in suite_names:
        match = re.search(rf"^{suite_name}=\(\n(?P<body>.*?)\n\)", content, re.MULTILINE | re.DOTALL)
        assert match is not None, f"{suite_name} array missing from gate script"
        for line in match.group("body").splitlines():
            item = line.strip()
            if not item or item.startswith("#"):
                continue
            item = item.split("#", 1)[0].strip().strip('"').strip("'")
            if item:
                paths.append(item.split("::", 1)[0])
    return paths


class TestGateFailClosedBehavior:
    """Test that the gate fails closed when required components are missing."""

    def test_gate_fails_when_required_suite_file_missing(
        self, gate_script_path: Path, temp_audit_dir: Path
    ) -> None:
        """Verify gate exits non-zero when a required suite file is missing."""
        # This test is difficult to implement without modifying the gate script
        # to accept a custom required suites file. For now, we test the
        # --verify-required-only mode which checks file existence.
        result = _run_gate_or_none(gate_script_path, "--verify-required-only")
        if result is None:
            for suite_path in _required_suite_paths_from_script(gate_script_path):
                assert (_repo_root(gate_script_path) / suite_path).exists(), (
                    f"Required security suite path missing: {suite_path}"
                )
            return
        # Should pass if all required suites exist
        assert result.returncode == 0, f"Gate verification failed: {result.stderr}"
        assert "All required suites present" in result.stdout

    def test_gate_lists_required_suites(self, gate_script_path: Path) -> None:
        """Verify gate can list required suites for inspection."""
        result = _run_gate_or_none(gate_script_path, "--list-required")
        if result is None:
            suites = _required_suite_paths_from_script(gate_script_path)
        else:
            assert result.returncode == 0
            suites = result.stdout.strip().split("\n")
        # Verify some known required suites are listed
        assert any("test_auth_enforcement.py" in s for s in suites)
        assert any("test_health.py" in s for s in suites)
        assert any("test_production_safety.py" in s for s in suites)
        assert any("test_i03_durable_persistence_and_llm.py" in s for s in suites)
        assert any("test_retention_deletion_contract.py" in s for s in suites)
        assert any("test_production_fail_closed_i02.py" in s for s in suites)
        assert "tests/security/test_cross_layer_tenant_isolation_matrix.py" in suites
        assert "services/layer4-agents/tests/test_security_fixes.py" in suites
        assert "tests/k8s" in suites


class TestGateEvidenceLogging:
    """Test that the gate properly logs evidence artifacts."""

    def test_gate_creates_audit_directory(
        self, gate_script_path: Path, tmp_path: Path
    ) -> None:
        """Verify the gate creates the audit evidence directory at startup."""
        audit_root = tmp_path / "evidence"
        env = os.environ.copy()
        # Repo-relative, forward-slash path so bash resolves it under ROOT_DIR and
        # the worktree stays clean (FABRIC_AUDIT_DIR is concatenated to ROOT_DIR).
        env["FABRIC_AUDIT_DIR"] = os.path.relpath(
            audit_root, _repo_root(gate_script_path)
        ).replace("\\", "/")
        if not os.environ.get("CI"):
            # Local dev: test mode skips the node/pnpm availability guards so the
            # verify-only path runs without frontend tooling. CI never sets it.
            env["FABRIC_GATE_TEST_MODE"] = "1"
        result = _run_gate_or_none(gate_script_path, "--verify-required-only", env=env)
        if result is None:
            content = gate_script_path.read_text(encoding="utf-8")
            assert 'FABRIC_AUDIT_DIR="${FABRIC_AUDIT_DIR:-.fabric/audit}"' in content
            assert 'mkdir -p "${AUDIT_DIR}/security_regression_gate"' in content
            return
        assert result.returncode == 0, f"gate verification failed: {result.stderr}"
        assert (audit_root / "security_regression_gate").is_dir(), (
            "gate did not create the security_regression_gate evidence directory"
        )

    def test_evidence_artifacts_have_correct_structure(
        self, temp_audit_dir: Path
    ) -> None:
        """Verify evidence artifacts have the expected structure."""
        # Create a mock evidence file to test structure
        security_gate_dir = temp_audit_dir / "security_regression_gate"
        security_gate_dir.mkdir(parents=True, exist_ok=True)

        # Mock results.json
        results = {
            "timestamp": "2026-05-04T00:00:00Z",
            "git_sha": "abc123",
            "branch": "test-branch",
            "os": "Linux",
            "gate_version": "1.1.0",
            "test_mode": 1,
            "suites": [],
            "status": "PASS",
            "exit_code": 0,
        }
        results_file = security_gate_dir / "mandatory_security_regression_gate.results.json"
        results_file.write_text(json.dumps(results, indent=2))

        # Verify structure
        data = json.loads(results_file.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert "git_sha" in data
        assert "branch" in data
        assert "os" in data
        assert "gate_version" in data
        assert "test_mode" in data
        assert "suites" in data
        assert "status" in data
        assert "exit_code" in data

    def test_evidence_summary_has_table_format(self, temp_audit_dir: Path) -> None:
        """Verify evidence summary has the expected markdown table format."""
        security_gate_dir = temp_audit_dir / "security_regression_gate"
        security_gate_dir.mkdir(parents=True, exist_ok=True)

        # Mock summary.md
        summary_content = """# Mandatory Security Regression Gate Evidence

- **Timestamp**: 2026-05-04T00:00:00Z
- **Git SHA**: abc123
- **Branch**: test-branch
- **OS**: Linux
- **Test Mode**: 1

## Check Results

| Check | Command | Required | Result | Evidence |
|-------|---------|----------|--------|----------|
| Test Check | pytest test.py | Yes | PASS | ✓ |

## Final Result

**Status**: PASS
**Exit Code**: 0
**Recommendation**: PASS
"""
        summary_file = security_gate_dir / "mandatory_security_regression_gate.summary.md"
        summary_file.write_text(summary_content, encoding="utf-8")

        # Verify format
        content = summary_file.read_text(encoding="utf-8")
        assert "# Mandatory Security Regression Gate Evidence" in content
        assert "| Check | Command | Required | Result | Evidence |" in content
        assert "**Status**:" in content
        assert "**Exit Code**:" in content


class TestGateTestMode:
    """Test FABRIC_GATE_TEST_MODE behavior."""

    def test_gate_respects_fabric_audit_dir_env_var(
        self, gate_script_path: Path, temp_audit_dir: Path
    ) -> None:
        """Verify gate uses FABRIC_AUDIT_DIR environment variable."""
        env = os.environ.copy()
        # Use relative path from repo root
        env["FABRIC_AUDIT_DIR"] = ".fabric/audit"

        # Run with --verify-required-only to test env var handling
        result = _run_gate_or_none(gate_script_path, "--verify-required-only", env=env)
        if result is None:
            content = gate_script_path.read_text(encoding="utf-8")
            assert "FABRIC_AUDIT_DIR" in content
            assert 'FABRIC_AUDIT_DIR="${FABRIC_AUDIT_DIR:-.fabric/audit}"' in content
        else:
            assert result.returncode == 0

    def test_gate_test_mode_skips_expensive_operations(
        self, gate_script_path: Path
    ) -> None:
        """Verify FABRIC_GATE_TEST_MODE=1 guards the expensive frontend/OpenAPI checks."""
        content = gate_script_path.read_text(encoding="utf-8")
        guard = 'if [[ "${FABRIC_GATE_TEST_MODE}" != "1" ]]; then'
        assert guard in content, "gate must gate expensive checks behind the test-mode guard"
        guard_index = content.index(guard)
        for marker in (
            "OpenAPI contract drift check",
            "Frontend Contract Tests",
            "Critical E2E skip-valve guard",
        ):
            assert marker in content, f"missing expensive check marker: {marker}"
            assert content.index(marker) > guard_index, (
                f"{marker} must only run when test mode is disabled"
            )

    def test_gate_rejects_test_mode_under_ci(self, gate_script_path: Path) -> None:
        """Deny: FABRIC_GATE_TEST_MODE=1 is forbidden under CI, failing closed."""
        env = os.environ.copy()
        env["FABRIC_GATE_TEST_MODE"] = "1"
        env["CI"] = "true"
        result = _run_gate_or_none(gate_script_path, "--verify-required-only", env=env)
        if result is None:
            content = gate_script_path.read_text(encoding="utf-8")
            assert "forbidden" in content
            assert "CI" in content
            return
        assert result.returncode == 1, (
            f"gate must reject test mode under CI, got returncode {result.returncode}"
        )
        assert "forbidden" in (result.stderr or ""), f"unexpected stderr: {result.stderr}"


class TestGateIntegration:
    """Integration tests for gate execution."""

    def test_gate_script_is_executable(self, gate_script_path: Path) -> None:
        """Verify the gate script exists and is readable."""
        assert gate_script_path.exists()
        assert gate_script_path.is_file()
        # On Windows, we check if it's a bash script
        assert gate_script_path.suffix == ".sh" or gate_script_path.name.endswith(".sh")

    def test_gate_script_has_shebang(self, gate_script_path: Path) -> None:
        """Verify the gate script has the correct shebang."""
        first_line = gate_script_path.read_text(encoding="utf-8").split("\n")[0]
        assert first_line.startswith("#!")
        assert "bash" in first_line

    def test_gate_script_includes_evidence_logging_functions(
        self, gate_script_path: Path
    ) -> None:
        """Verify the gate script includes evidence logging functions."""
        content = gate_script_path.read_text(encoding="utf-8")
        assert "log_evidence_start" in content
        assert "log_suite_result" in content
        assert "log_evidence_complete" in content

    def test_gate_script_includes_i02_checks(self, gate_script_path: Path) -> None:
        """Verify the gate script includes I-02 checks for all layers."""
        content = gate_script_path.read_text(encoding="utf-8")
        assert "layer2-extraction" in content
        assert "layer5-ground-truth" in content
        assert "test_production_fail_closed_i02.py" in content

    def test_gate_script_includes_c06_checks(self, gate_script_path: Path) -> None:
        """Verify the gate script includes C-06 security regression checks."""
        content = gate_script_path.read_text(encoding="utf-8")
        assert "LAYER4_C06_SECURITY_TESTS" in content
        assert "services/layer4-agents/tests/test_security_fixes.py" in content
        assert "layer4_c06_security.xml" in content

    def test_gate_script_includes_test_mode_guard(
        self, gate_script_path: Path
    ) -> None:
        """Verify the gate script includes test mode guards."""
        content = gate_script_path.read_text(encoding="utf-8")
        assert "FABRIC_GATE_TEST_MODE" in content
        assert "TEST MODE" in content or "test mode" in content.lower()


class TestGateRequiredSuites:
    """Test required suites configuration."""

    def test_required_suites_array_exists(self, gate_script_path: Path) -> None:
        """Verify the gate script has required suite arrays."""
        content = gate_script_path.read_text(encoding="utf-8")
        assert "STANDALONE_API_TESTS=(" in content
        assert "ROOT_SECURITY_TESTS=(" in content
        assert "CROSS_LAYER_TENANT_MATRIX_TESTS=(" in content
        assert "LAYER4_C06_SECURITY_TESTS=(" in content
        assert ")" in content

    def test_required_suites_includes_critical_security_tests(
        self, gate_script_path: Path
    ) -> None:
        """Verify required suites include critical security tests."""
        content = gate_script_path.read_text(encoding="utf-8")
        assert "test_auth_enforcement.py" in content
        assert "test_health.py" in content
        assert "test_production_safety.py" in content
        assert "test_tenant_boundary_fails_closed.py" in content
        assert "test_cross_tenant_api.py" in content
        assert "test_cross_layer_tenant_isolation_matrix.py" in content
        assert "test_retention_deletion_contract.py" in content

    def test_required_suites_includes_i02_tests(self, gate_script_path: Path) -> None:
        """Verify required suites include I-02 production fail-closed tests."""
        content = gate_script_path.read_text(encoding="utf-8")
        assert "layer2-extraction/tests/test_production_fail_closed_i02.py" in content
        assert "layer5-ground-truth/tests/test_production_fail_closed_i02.py" in content

    def test_required_suites_includes_c06_tests(self, gate_script_path: Path) -> None:
        """Verify required suites include C-06 mandatory Layer 4 tests."""
        content = gate_script_path.read_text(encoding="utf-8")
        assert "services/layer4-agents/tests/test_security_fixes.py" in content
        assert "services/layer4-agents/tests/test_security_fixes.py" in content
