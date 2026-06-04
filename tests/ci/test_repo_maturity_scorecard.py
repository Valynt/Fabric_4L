from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "reports" / "generate_repo_maturity_scorecard.py"
SCHEMA = REPO_ROOT / "reports" / "scorecards" / "repo-maturity.schema.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_repo_maturity_scorecard", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str = "evidence") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _create_ready_repo(root: Path) -> None:
    _write(root / "apps/web/package.json", '{"scripts":{"test":"vitest"}}')
    _write(root / "services/layer1-ingestion/Dockerfile", "FROM python:3.12\n")
    _write(root / "contracts/GOVERNANCE.md", "# Contract Governance\n")
    _write(root / "contracts/openapi/layer1.yaml", "openapi: 3.1.0\n")
    _write(root / "docs/reference/layer-runtime-path-governance.md", "# Runtime paths\n")
    _write(root / ".github/workflows/pr-checks.yml", "structural-preflight\ntenant-isolation-gate\n")
    _write(root / ".github/workflows/contract-compliance.yml", "contract-scorecard\n")
    _write(root / ".github/workflows/prod-readiness.yml", "gate-release-policy\ngate-obs\n")
    _write(root / ".github/workflows/critical-gates.yml", "p0\n")
    _write(root / ".github/workflows/security-validation.yml", "security\n")
    _write(root / ".github/workflows/release-evidence-bundle.yml", "release\n")
    _write(root / "docker-compose.dev.yml", "services: {}\n")
    _write(root / "docker-compose.full.yml", "services: {}\n")
    _write(root / "k8s/base/externalsecret-app.yaml", "kind: ExternalSecret\n")
    _write(root / "pytest.ini", "[pytest]\nmarkers = tenant_boundary\n")
    _write(root / "tests/security/test_tenant.py", "def test_tenant(): pass\n")
    _write(root / "tests/contract/test_contract.py", "def test_contract(): pass\n")
    _write(root / "tests/backend_integrated/test_smoke.py", "def test_smoke(): pass\n")
    _write(root / ".env.example", "ENVIRONMENT=development\n")
    _write(root / ".fabric/prod-gates.policy.yaml", "version: 1\n")
    _write(root / "config/ci/test_skip_register.yaml", "skips: []\n")
    _write(root / "monitoring/prometheus.yml", "global: {}\n")
    _write(root / "docs/slo/performance-slo.v1.json", "{}")
    _write(root / "docs/readiness/observability-deployment-readiness.md", "# Observability\n")
    _write(root / "Makefile", "verify:\n\t@echo verify\n")
    _write(root / "scripts/ops/release-gate.sh", "#!/usr/bin/env bash\n")
    _write(root / "scripts/security/zero_trust_checks.sh", "#!/usr/bin/env bash\n")
    _write(root / "scripts/ci/run_root_aggregate_checks.py", "print('ok')\n")
    _write(root / "docs/README.md", "# Docs\n")
    _write(root / "DESIGN.md", "# Design\n")
    _write(root / "docs/runbooks/00-runbook-index.md", "# Runbooks\n")
    _write(root / "SECURITY.md", "# Security\n")
    _write(root / "docs/LAUNCH_RUNBOOK.md", "# Launch\n")
    _write(root / "docs/governance/production-readiness-p0-foundations.md", "# P0\n")
    _write(root / "docs/audit/production-readiness-2026-05-27.md", "# Audit\n")
    _write(root / "reports/production-launch-readiness-audit.md", "# Audit\n")
    _write(
        root / "docs/PRODUCTION_READINESS_CHECKLIST.md",
        "\n".join(
            [
                "| # | Check | Criteria | Priority | Status |",
                "|---|-------|----------|----------|--------|",
                "| S1 | **Artifact signatures verified** | cosign verify passes | P0 | PASS |",
                "| R1 | **Health checks configured** | probes configured | P0 | PASS |",
                "| T2 | **P1 security tests present** | tests present | P1 | PARTIAL |",
            ]
        )
        + "\n",
    )


def test_main_generates_default_scorecard_and_shape(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _create_ready_repo(tmp_path)
    monkeypatch.setattr(module, "ROOT", tmp_path)

    assert module.main(["--no-fail"]) == 0

    output = tmp_path / "reports/scorecards/repo-maturity.json"
    data = json.loads(output.read_text(encoding="utf-8"))
    assert module.validate_scorecard_shape(data) == []
    assert data["status"] == "pass"
    assert data["overall_score"] == 10.0


def test_schema_declares_required_machine_readable_fields() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required = set(schema["required"])

    assert {
        "schema_version",
        "generated_at",
        "status",
        "overall_score",
        "max_score",
        "dimensions",
        "p0_gates",
        "required_checks",
        "source_reports",
    } <= required
    assert schema["properties"]["dimensions"]["minItems"] == 11


def test_every_dimension_has_evidence_link(tmp_path: Path) -> None:
    module = _load_module()
    _create_ready_repo(tmp_path)

    report = module.compute_scorecard(tmp_path)

    assert len(report["dimensions"]) == 11
    assert all(dimension["evidence"] for dimension in report["dimensions"])
    assert all(
        "path" in item and "check" in item
        for dimension in report["dimensions"]
        for item in dimension["evidence"]
    )


def test_missing_p0_automation_causes_nonzero_status(tmp_path: Path) -> None:
    module = _load_module()
    _create_ready_repo(tmp_path)
    (tmp_path / ".github/workflows/critical-gates.yml").unlink()

    report = module.compute_scorecard(tmp_path)

    assert report["status"] == "fail"
    assert report["overall_score"] < 10.0
    assert any(
        gate["id"] == "critical_security_workflow" and gate["status"] == "missing"
        for gate in report["p0_gates"]
    )


def test_p0_partial_prevents_ten_out_of_ten(tmp_path: Path) -> None:
    module = _load_module()
    _create_ready_repo(tmp_path)
    checklist = tmp_path / "docs/PRODUCTION_READINESS_CHECKLIST.md"
    text = checklist.read_text(encoding="utf-8")
    checklist.write_text(text.replace("| R1 | **Health checks configured** | probes configured | P0 | PASS |", "| R1 | **Health checks configured** | probes configured | P0 | PARTIAL |"), encoding="utf-8")

    report = module.compute_scorecard(tmp_path)

    assert report["status"] == "fail"
    assert report["overall_score"] < 10.0
    assert any(gate["id"] == "R1" and gate["status"] == "partial" for gate in report["p0_gates"])


def test_all_required_checks_passing_is_only_path_to_ten(tmp_path: Path) -> None:
    module = _load_module()
    _create_ready_repo(tmp_path)

    ready = module.compute_scorecard(tmp_path)
    assert ready["overall_score"] == 10.0
    assert all(check["status"] == "pass" for check in ready["required_checks"])

    (tmp_path / "scripts/ops/release-gate.sh").unlink()
    blocked = module.compute_scorecard(tmp_path)

    assert any(check["status"] == "fail" for check in blocked["required_checks"])
    assert blocked["overall_score"] < 10.0


def _readiness_summary(status_by_key: dict[str, str]) -> dict:
    return {
        "results": [
            {"key": key, "status": status, "summary": f"{key} {status}"}
            for key, status in status_by_key.items()
        ]
    }


def test_readiness_threshold_scorecard_fails_below_minimum(monkeypatch) -> None:
    module = _load_module()
    statuses = {key: "passed" for key in module.READINESS_DIMENSION_KEYS}
    statuses["security_suite"] = "failed"
    monkeypatch.setattr(
        module,
        "_readiness_regressions",
        lambda root=module.ROOT: [{"id": "demo", "status": "pass", "description": "ok"}],
    )

    report = module.build_readiness_threshold_scorecard(_readiness_summary(statuses), min_score=10)

    assert report["status"] == "fail"
    assert report["overall_score"] == 9.0
    assert any("security_suite" in failure for failure in report["failure_summary"])
    assert any("below required 10/10" in failure for failure in report["failure_summary"])


def test_readiness_threshold_scorecard_passes_only_at_ten(monkeypatch) -> None:
    module = _load_module()
    statuses = {key: "passed" for key in module.READINESS_DIMENSION_KEYS}
    monkeypatch.setattr(
        module,
        "_readiness_regressions",
        lambda root=module.ROOT: [{"id": "demo", "status": "pass", "description": "ok"}],
    )

    report = module.build_readiness_threshold_scorecard(_readiness_summary(statuses), min_score=10)

    assert report["status"] == "pass"
    assert report["overall_score"] == 10.0
    assert report["failure_summary"] == []


def test_readiness_threshold_scorecard_writes_final_artifacts(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    statuses = {key: "passed" for key in module.READINESS_DIMENSION_KEYS}
    monkeypatch.setattr(
        module,
        "_readiness_regressions",
        lambda root=module.ROOT: [{"id": "demo", "status": "pass", "description": "ok"}],
    )
    report = module.build_readiness_threshold_scorecard(_readiness_summary(statuses), min_score=10)

    module.write_scorecard(report, tmp_path)

    assert (tmp_path / "repo-maturity-scorecard.json").exists()
    assert (tmp_path / "repo-maturity-scorecard.md").exists()
