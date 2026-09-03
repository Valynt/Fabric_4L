#!/usr/bin/env python3
"""Run the first-class tenant isolation gate.

The gate is intentionally explicit instead of marker-only. Tenant isolation
coverage spans static checks, service-local tests, PostgreSQL RLS tests, graph
tests, background job tests, and cache isolation tests that live in different
parts of the repository. Grouping those targets here keeps local and CI output
layer-oriented while preserving each suite's native test location.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = REPO_ROOT / "artifacts" / "tenant-isolation" / "summary.json"
PYTEST_BASE_ARGS = ("-v", "--tb=short")


@dataclass(frozen=True)
class TenantIsolationGroup:
    id: str
    title: str
    targets: tuple[str, ...]
    cwd: Path = REPO_ROOT


GROUPS: tuple[TenantIsolationGroup, ...] = (
    TenantIsolationGroup(
        id="cross-layer",
        title="Cross-Layer Tenant Matrix",
        targets=(
            "tests/security/test_cross_layer_tenant_isolation_matrix.py",
            "tests/security/test_tenant_boundary_fails_closed.py",
            "tests/security/test_tenant_repository_filter_presence.py",
        ),
    ),
    TenantIsolationGroup(
        id="l1-rls-jobs",
        title="L1 PostgreSQL RLS And Jobs",
        cwd=REPO_ROOT / "services" / "layer1-ingestion",
        targets=(
            "tests/security/test_rls_enforcement_postgres.py",
            "tests/security/test_celery_tenant_isolation_postgres.py",
            "tests/security/test_targets_tenant_isolation.py",
            "tests/test_api_tenant_propagation.py",
            "tests/test_cross_tenant_hostile.py",
        ),
    ),
    TenantIsolationGroup(
        id="l2-extraction",
        title="L2 Extraction Tenant Context",
        targets=(
            "services/layer2-extraction/tests/test_api_tenant_propagation.py",
            "services/layer2-extraction/tests/test_cross_tenant_hostile.py",
            "services/layer2-extraction/tests/test_missing_tenant_context_hostile.py",
            "services/layer2-extraction/tests/test_job_store.py",
            "services/layer2-extraction/tests/test_extraction_cache.py",
        ),
    ),
    TenantIsolationGroup(
        id="l3-graph",
        title="L3 Knowledge Graph Tenant Boundary",
        targets=(
            "tests/security/test_graph_tenant_hostile_regression.py",
            "tests/security/test_neo4j_tenant_write_enforcement.py",
            "tests/security/test_neo4j_cross_tenant_write_isolation.py",
            "services/layer3-knowledge/tests/test_api_tenant_propagation.py",
            "services/layer3-knowledge/tests/test_cross_tenant_hostile.py",
            "services/layer3-knowledge/tests/test_tenant_isolation.py",
        ),
    ),
    TenantIsolationGroup(
        id="l4-agents-jobs",
        title="L4 Agents Workflow And Job Tenant Context",
        targets=(
            "services/layer4-agents/tests/test_api_tenant_propagation.py",
            "services/layer4-agents/tests/test_cross_tenant_hostile.py",
            "services/layer4-agents/tests/test_agent_tenant_isolation.py",
            "services/layer4-agents/tests/test_workflow_tenant_isolation.py",
            "services/layer4-agents/tests/test_checkpoint_tenant_isolation.py",
        ),
    ),
    TenantIsolationGroup(
        id="l5-ground-truth",
        title="L5 Ground Truth Tenant Isolation",
        cwd=REPO_ROOT / "services" / "layer5-ground-truth",
        targets=(
            "tests/test_tenant_id_consistency.py",
            "tests/test_api.py::TestGetTruth::test_org_isolation",
            "tests/test_cross_tenant_hostile.py",
            "tests/unit/test_truth_service_and_api_tenant_boundaries.py",
        ),
    ),
    TenantIsolationGroup(
        id="l6-benchmarks",
        title="L6 Benchmarks Tenant Isolation",
        targets=(
            "services/layer6-benchmarks/tests/test_api_tenant_propagation.py",
            "services/layer6-benchmarks/tests/test_repository_tenant_isolation.py",
            "services/layer6-benchmarks/tests/test_cross_tenant_hostile.py",
        ),
    ),
    TenantIsolationGroup(
        id="cache",
        title="Shared Cache Isolation",
        targets=(
            "tests/cache/test_redis_tenant_isolation.py",
            "tests/shared/identity/test_api_key_cache.py",
            "services/api/app/tests/test_distributed_session_store.py",
        ),
    ),
    TenantIsolationGroup(
        id="hostile-tenancy-contracts",
        title="Hostile Tenancy Contracts & Surface Isolation",
        targets=(
            "tests/tenancy/test_hostile_tenancy_contracts.py",
            "tests/tenancy/test_file_storage_tenant_scope.py",
            "tests/tenancy/test_search_index_tenant_scope.py",
        ),
    ),
)


def _target_path(target: str) -> str:
    return target.split("::", 1)[0]


def _missing_targets(group: TenantIsolationGroup) -> list[str]:
    return [
        target
        for target in group.targets
        if not (group.cwd / Path(_target_path(target))).exists()
    ]


def _gate_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    shared_pkg = str(REPO_ROOT / "packages" / "shared" / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    pythonpath_entries = [shared_pkg, str(REPO_ROOT)]
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return env


def _run_group(group: TenantIsolationGroup) -> dict[str, object]:
    print(f"\n=== {group.title} ({group.id}) ===", flush=True)
    print(f"cwd: {group.cwd.relative_to(REPO_ROOT) if group.cwd != REPO_ROOT else '.'}", flush=True)

    missing = _missing_targets(group)
    if missing:
        for target in missing:
            print(f"missing target: {target}", flush=True)
        return {
            "id": group.id,
            "title": group.title,
            "cwd": str(group.cwd.relative_to(REPO_ROOT) if group.cwd != REPO_ROOT else "."),
            "targets": list(group.targets),
            "status": "fail",
            "exit_code": 2,
            "missing_targets": missing,
        }

    command = (sys.executable, "-m", "pytest", *PYTEST_BASE_ARGS, *group.targets)
    result = subprocess.run(command, cwd=group.cwd, env=_gate_env(), check=False)
    return {
        "id": group.id,
        "title": group.title,
        "cwd": str(group.cwd.relative_to(REPO_ROOT) if group.cwd != REPO_ROOT else "."),
        "targets": list(group.targets),
        "status": "pass" if result.returncode == 0 else "fail",
        "exit_code": result.returncode,
        "missing_targets": [],
    }


def _git_commit_sha() -> str:
    result = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _archive_summary(summary_path: Path, generated_at_utc: str) -> Path:
    archive_name = generated_at_utc[:10] + "-hostile-tenant-isolation-l1-l7-api"
    archive_dir = summary_path.parent / "archive" / archive_name
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / "summary.json"
    shutil.copy2(summary_path, archive_path)
    return archive_path


def _write_summary(results: list[dict[str, object]]) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    failed = [result for result in results if result["status"] != "pass"]
    generated_at_utc = datetime.now(timezone.utc).isoformat()
    command = " ".join((sys.executable, "scripts/ci/run_tenant_isolation_gate.py"))
    payload = {
        "gate": "tenant-isolation-hostile-l1-l7-api",
        "generated_at_utc": generated_at_utc,
        "commit_sha": _git_commit_sha(),
        "command": command,
        "status": "pass" if not failed else "fail",
        "summary": {
            "groups": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
        },
        "groups": results,
    }
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nTenant isolation summary written to {SUMMARY_PATH.relative_to(REPO_ROOT)}", flush=True)
    if failed:
        print("Tenant isolation summary was not archived because the gate failed.", flush=True)
    else:
        archive_path = _archive_summary(SUMMARY_PATH, generated_at_utc)
        print(f"Tenant isolation summary archived to {archive_path.relative_to(REPO_ROOT)}", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        print("run_tenant_isolation_gate.py does not accept arguments", file=sys.stderr)
        return 2

    results = [_run_group(group) for group in GROUPS]
    _write_summary(results)

    failed = [result for result in results if result["status"] != "pass"]
    if failed:
        print("\nTenant isolation gate failed groups:", flush=True)
        for result in failed:
            print(f"- {result['id']} ({result['exit_code']})", flush=True)
        return 1

    print("\nTenant isolation gate passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
