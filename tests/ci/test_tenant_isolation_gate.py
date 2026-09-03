from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_root_isolation_script_uses_first_class_runner() -> None:
    package_json = _read("package.json")

    assert '"test:isolation": "python scripts/ci/run_root_aggregate_checks.py isolation"' in package_json


def test_tenant_isolation_runner_groups_required_boundaries() -> None:
    script_path = REPO_ROOT / "scripts" / "ci" / "run_tenant_isolation_gate.py"
    module = ast.parse(script_path.read_text(encoding="utf-8"))
    constants = {
        value
        for node in ast.walk(module)
        if isinstance(node, ast.Constant) and isinstance((value := node.value), str)
    }

    expected_group_ids = {
        "cross-layer",
        "l1-rls-jobs",
        "l2-extraction",
        "l3-graph",
        "l4-agents-jobs",
        "l5-ground-truth",
        "l6-benchmarks",
        "cache",
    }
    assert expected_group_ids <= constants

    expected_targets = {
        "tests/security/test_cross_layer_tenant_isolation_matrix.py",
        "tests/security/test_tenant_boundary_fails_closed.py",
        "tests/security/test_rls_enforcement_postgres.py",
        "tests/security/test_celery_tenant_isolation_postgres.py",
        "services/layer3-knowledge/tests/test_tenant_isolation.py",
        "services/layer4-agents/tests/test_workflow_tenant_isolation.py",
        "tests/test_api.py::TestGetTruth::test_org_isolation",
        "services/layer6-benchmarks/tests/test_repository_tenant_isolation.py",
        "tests/cache/test_redis_tenant_isolation.py",
    }
    assert expected_targets <= constants


def test_ci_uses_first_class_tenant_isolation_gate() -> None:
    pr_checks = _read(".github/workflows/pr-checks.yml")
    critical_gates = _read(".github/workflows/critical-gates.yml")

    assert "tenant-isolation-gate:" in pr_checks
    assert "name: Tenant Isolation Gate" in pr_checks
    assert "python scripts/ci/run_tenant_isolation_gate.py" in pr_checks
    assert "- tenant-isolation-gate" in pr_checks
    assert '["tenant-isolation-gate"]="${{ needs.tenant-isolation-gate.result }}"' in pr_checks
    assert 'command: "pnpm test:isolation"' in critical_gates


def test_pytest_marker_inventory_includes_tenant_isolation() -> None:
    pytest_ini = _read("pytest.ini")
    assert "tenant_isolation: First-class tenant isolation gate tests" in pytest_ini
    assert "tenant_boundary: High-risk tenant boundary tests" in pytest_ini
    assert "tenant_matrix: Cross-layer route-to-hostile-test tenant isolation matrix coverage tests" in pytest_ini
    assert "cross_tenant_write: cross-tenant write isolation regression tests" in pytest_ini


def test_critical_tenant_isolation_gate_provisions_redis() -> None:
    critical_gates = _read(".github/workflows/critical-gates.yml")

    assert "services:" in critical_gates
    assert "redis:" in critical_gates
    assert '--health-cmd "redis-cli ping"' in critical_gates


def test_tenant_isolation_gate_provides_strict_auth_and_shared_paths() -> None:
    pr_checks = _read(".github/workflows/pr-checks.yml")

    tenant_job = pr_checks.split("  tenant-isolation-gate:", 1)[1].split("  critical-behaviors-gate:", 1)[0]
    assert "FABRIC_AUTH_PUBLIC_KEYS=%s" in tenant_job
    assert "cat config/ci/fabric_auth_test_public_keys.json" in tenant_job
    assert "PYTHONPATH: ${{ github.workspace }}/packages/shared/src:${{ github.workspace }}/services/layer4-agents/src:${{ github.workspace }}/services/layer5-ground-truth/src" in tenant_job
    assert "layer7-billing" not in tenant_job
    assert "python -m pip install --require-hashes -r tests/requirements-test.lock" in tenant_job


def test_layer1_database_defers_sync_engine_until_session_use() -> None:
    source = _read("services/layer1-ingestion/src/layer1_ingestion/shared/database.py")

    assert "except ModuleNotFoundError as exc:" in source
    assert "SessionLocal = sessionmaker(autocommit=False, autoflush=False)" in source
    assert "def _ensure_session_factory_bound() -> None:" in source
    assert "def _new_session() -> Session:" in source
    assert "Layer 1 sync database adapter unavailable; install psycopg2 before opening sync database sessions." in source
