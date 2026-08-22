from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
REGISTRY = WORKFLOW_DIR / "workflow-registry.json"
PLAN = REPO_ROOT / "docs" / "operations" / "ci-workflow-consolidation.md"

CANONICAL_WORKFLOWS = {
    "pr-checks.yml",
    "security-gates.yml",
    "contract-compliance.yml",
    "prod-readiness.yml",
    "codeql.yml",
    "chaos-testing.yml",
    "dr-drill.yml",
    "k8s-readiness.yml",
    "repo-hygiene.yml",
    "supply-chain-integrity.yml",
    "performance-load-tests.yml",
}

RETIRED_WORKFLOWS = {
    "audit-snapshot.yml",
    "chaos-engineering.yml",
    "chaos-smoke.yml",
    "ci-failure-backlog.yml",
    "cleanup-branches.yml",
    "codeql-analysis.yml",
    "compliance-evidence-integrity.yml",
    "game-day-evidence.yml",
    "integration-tests.yml",
    "k8s-validation.yml",
    "launch-readiness.yml",
    "layer6-dashboard-metric-drift.yml",
    "live-workflow-validation.yml",
    "package-manager-policy.yml",
    "package-sign.yml",
    "performance-baseline.yml",
    "pr-performance-gate.yml",
    "preflight.yml",
    "production-readiness-check.yml",
    "refresh-testing-kpis.yml",
    "regenerate-sdk.yml",
    "restore-verification.yml",
    "secret-guardrails.yml",
    "security-validation.yml",
    "smoke-gate.yml",
    "stale.yml",
    "test-mandatory.yml",
    "test.yml",
    "verify-gate.yml",
    "workflow-readme-sync-check.yml",
}

CONSOLIDATION_PROOF_CANDIDATES = {
    "codeql-analysis.yml": {
        "canonical": ["codeql.yml"],
        "status": "retired-recorded",
        "risk": "needs branch-protection update",
        "required_phrase": "both CodeQL workflows were blocking",
    },
    "chaos-smoke.yml": {
        "canonical": ["chaos-testing.yml"],
        "status": "retired-recorded",
        "risk": "needs branch-protection update",
        "required_phrase": "PR-triggered and blocking",
    },
    "deploy.yml": {
        "canonical": ["build-deploy.yml", "environment-promotion.yml"],
        "status": "present-blocked",
        "risk": "not safe",
        "required_phrase": "workflow-call deployment behavior",
    },
}


def _workflow_files() -> set[str]:
    return {
        path.name
        for path in WORKFLOW_DIR.iterdir()
        if path.suffix in {".yml", ".yaml"}
    }


def _registry_workflows() -> set[str]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {Path(workflow["path"]).name for workflow in data["workflows"]}


def _registry_workflow_map() -> dict[str, dict]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {
        Path(workflow["path"]).name: workflow
        for workflow in data["workflows"]
    }


def _workflow_data(workflow: str) -> dict:
    data = yaml.safe_load((WORKFLOW_DIR / workflow).read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{workflow} should parse as a workflow mapping"
    return data


def _workflow_triggers(workflow: str) -> set[str]:
    triggers = _workflow_data(workflow).get("on", _workflow_data(workflow).get(True, {}))
    if isinstance(triggers, str):
        return {triggers}
    if isinstance(triggers, list):
        return {str(trigger) for trigger in triggers}
    if isinstance(triggers, dict):
        return {str(trigger) for trigger in triggers}
    return set()


def _workflow_jobs(workflow: str) -> set[str]:
    jobs = _workflow_data(workflow).get("jobs", {})
    assert isinstance(jobs, dict), f"{workflow} should define jobs"
    return set(jobs)


def test_ci_workflow_consolidation_plan_names_canonical_owners() -> None:
    content = PLAN.read_text(encoding="utf-8")

    for workflow in CANONICAL_WORKFLOWS:
        assert workflow in content
        assert (WORKFLOW_DIR / workflow).exists(), f"Missing canonical workflow: {workflow}"


def test_ci_workflow_retired_candidates_are_documented_and_removed() -> None:
    content = PLAN.read_text(encoding="utf-8")
    workflow_files = _workflow_files()
    registry_workflows = _registry_workflows()

    for workflow in RETIRED_WORKFLOWS:
        assert workflow not in workflow_files, f"Retired workflow still exists: {workflow}"
        assert workflow not in registry_workflows, f"Retired workflow still registered: {workflow}"
        assert workflow in content


def test_ci_workflow_inventory_stays_within_s6_6_limit() -> None:
    workflow_files = _workflow_files()
    assert len(workflow_files) <= 56

    content = PLAN.read_text(encoding="utf-8")
    assert "at most 56 workflow YAML files" in content
    assert "workflow-registry.json" in content


def test_ci_workflow_cleanup_rules_preserve_required_gate_visibility() -> None:
    content = PLAN.read_text(encoding="utf-8")

    required_rules = [
        "Keep branch-protected check names aligned",
        "Add future workflow behavior as a job/profile",
        "Run `python scripts/ci/verify_workflow_registry.py`",
    ]
    for rule in required_rules:
        assert rule in content


def test_ci_workflow_consolidation_proof_records_deletion_risk() -> None:
    content = PLAN.read_text(encoding="utf-8")
    registry = _registry_workflow_map()
    workflow_files = _workflow_files()

    for workflow, proof in CONSOLIDATION_PROOF_CANDIDATES.items():
        assert workflow in content
        assert proof["status"] in content
        assert proof["risk"] in content
        assert proof["required_phrase"] in content

        for canonical in proof["canonical"]:
            assert canonical in content
            assert canonical in workflow_files

        if workflow not in workflow_files:
            assert proof["status"] == "retired-recorded"
            assert workflow not in registry
            continue

        assert proof["status"] == "present-blocked"
        assert workflow in registry
        duplicate = registry[workflow]
        canonical_entries = [registry[canonical] for canonical in proof["canonical"]]

        duplicate_triggers = _workflow_triggers(workflow)
        canonical_triggers = set().union(
            *(_workflow_triggers(canonical) for canonical in proof["canonical"])
        )
        duplicate_jobs = _workflow_jobs(workflow)
        canonical_jobs = set().union(
            *(_workflow_jobs(canonical) for canonical in proof["canonical"])
        )
        duplicate_secrets = set(duplicate.get("required_secrets", []))
        canonical_secrets = set().union(
            *(set(canonical.get("required_secrets", [])) for canonical in canonical_entries)
        )
        duplicate_artifacts = set(duplicate.get("produced_artifacts", []))
        canonical_artifacts = set().union(
            *(set(canonical.get("produced_artifacts", [])) for canonical in canonical_entries)
        )

        for trigger in duplicate_triggers - canonical_triggers:
            assert trigger in content
        for job in duplicate_jobs - canonical_jobs:
            assert job in content
        for secret in duplicate_secrets - canonical_secrets:
            assert secret in content
        for artifact in duplicate_artifacts - canonical_artifacts:
            assert artifact in content


def test_k8s_server_dry_run_creates_namespace_before_overlay_validation() -> None:
    workflow = (WORKFLOW_DIR / "k8s-readiness.yml").read_text(encoding="utf-8")
    server_job = workflow.split("  k8s-server-dry-run:", 1)[1].split("  k8s-deployment-validation:", 1)[0]

    assert "kubectl apply --dry-run=server -f k8s/base/namespace.yml" in server_job
    assert "kubectl apply -f k8s/base/namespace.yml" in server_job
    assert server_job.index("kubectl apply -f k8s/base/namespace.yml") < server_job.index(
        "kustomize build k8s/envs/dev --load-restrictor=LoadRestrictionsNone"
    )


def test_k8s_server_dry_run_renders_out_of_tree_env_overlays_with_kustomize() -> None:
    workflow = (WORKFLOW_DIR / "k8s-readiness.yml").read_text(encoding="utf-8")

    for overlay in ("dev", "prod"):
        render = f"kustomize build k8s/envs/{overlay} --load-restrictor=LoadRestrictionsNone"
        assert f"{render} | kubectl apply --dry-run=server -f -" in workflow
        assert f"kubectl apply --dry-run=server -k k8s/envs/{overlay}" not in workflow


def test_k8s_server_dry_runs_install_local_ci_crds_before_server_apply() -> None:
    readiness = (WORKFLOW_DIR / "k8s-readiness.yml").read_text(encoding="utf-8")
    readiness_job = readiness.split("  k8s-server-dry-run:", 1)[1]
    assert "kubectl apply -f k8s/ci/crds/" in readiness_job
    assert readiness_job.index("kubectl apply -f k8s/ci/crds/") < readiness_job.index(
        "kustomize build k8s/envs/dev --load-restrictor=LoadRestrictionsNone"
    )

    pr_checks = (WORKFLOW_DIR / "pr-checks.yml").read_text(encoding="utf-8")
    dry_run_job = pr_checks.split("  k8s-dry-run:", 1)[1].split("  contract-checks:", 1)[0]
    assert "kubectl apply -f k8s/ci/crds/" in dry_run_job
    assert dry_run_job.index("kubectl apply -f k8s/ci/crds/") < dry_run_job.index(
        "kustomize build k8s/deployments/dev-nginx --load-restrictor=LoadRestrictionsNone"
    )


def test_k8s_ci_dry_run_crds_cover_operator_backed_kinds() -> None:
    crd_docs = []
    for path in (REPO_ROOT / "k8s/ci/crds").glob("*.yaml"):
        crd_docs.extend(doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if doc)

    crds = {doc["metadata"]["name"]: doc for doc in crd_docs}
    assert crds["externalsecrets.external-secrets.io"]["spec"]["scope"] == "Namespaced"
    assert crds["clustersecretstores.external-secrets.io"]["spec"]["scope"] == "Cluster"
    assert crds["clusterpolicies.kyverno.io"]["spec"]["scope"] == "Cluster"
    assert crds["externalsecrets.external-secrets.io"]["spec"]["versions"][0]["name"] == "v1beta1"
    assert crds["clustersecretstores.external-secrets.io"]["spec"]["versions"][0]["name"] == "v1beta1"
    assert crds["clusterpolicies.kyverno.io"]["spec"]["versions"][0]["name"] == "v1"


def test_alertmanager_config_validation_uses_standalone_kustomize_for_deployment_overlay() -> None:
    workflow = (WORKFLOW_DIR / "pr-checks.yml").read_text(encoding="utf-8")
    job = workflow.split("  alertmanager-config-check:", 1)[1].split("  ci-summary:", 1)[0]

    assert "kustomize build k8s/deployments/dev-nginx --load-restrictor=LoadRestrictionsNone" in job
    assert "kubectl kustomize k8s/deployments/dev-nginx" not in job


def test_pr_contract_checks_use_maintained_endpoint_hook_registry() -> None:
    workflow = (WORKFLOW_DIR / "pr-checks.yml").read_text(encoding="utf-8")
    contract_job = workflow.split("  contract-checks:", 1)[1].split(
        "  production-readiness-gate:",
        1,
    )[0]
    registry_path = "apps/web/contracts/endpoint-hook-registry.json"

    assert f"--registry {registry_path}" in contract_job
    assert "docs/archive" not in contract_job
    assert (REPO_ROOT / registry_path).exists()
