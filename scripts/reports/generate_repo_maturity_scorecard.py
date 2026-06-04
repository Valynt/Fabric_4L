#!/usr/bin/env python3
"""Generate a machine-readable repository maturity scorecard."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = "reports/scorecards/repo-maturity.json"
DEFAULT_ARTIFACT_DIR = ROOT / "artifacts" / "readiness-10"
DEFAULT_READINESS_SUMMARY = DEFAULT_ARTIFACT_DIR / "readiness-10-summary.json"
SCORECARD_JSON = "repo-maturity-scorecard.json"
SCORECARD_MD = "repo-maturity-scorecard.md"
SCHEMA_VERSION = "1.0.0"
MAX_SCORE = 10.0
P0_FAILURE_SCORE_CAP = 9.0

READINESS_DIMENSION_KEYS: tuple[str, ...] = (
    "script_parity",
    "schema_index",
    "openapi_breaking_change",
    "migration_status",
    "security_suite",
    "tenant_isolation_suite",
    "router_gate",
    "ci_workflow_registry",
    "evidence_bundle_generation",
)

REQUIRED_PACKAGE_SCRIPTS: dict[str, str] = {
    "readiness:10": "python scripts/ci/readiness_10_gate.py",
    "test:schema": "python scripts/ci/run_root_aggregate_checks.py schema",
    "contract:breaking": "python scripts/ci/openapi_breaking_change_gate.py",
    "db:migrate:status": "python scripts/ci/run_root_aggregate_checks.py db-migrate-status",
    "test:security": "python -m pytest tests/security/ -v --tb=short",
    "test:isolation": "python scripts/ci/run_root_aggregate_checks.py isolation",
    "test:router": "python scripts/ci/run_root_aggregate_checks.py router",
}


@dataclass(frozen=True)
class Check:
    key: str
    description: str
    path: str
    contains: str | None = None
    glob: bool = False
    required: bool = True


@dataclass(frozen=True)
class Dimension:
    key: str
    name: str
    checks: tuple[Check, ...]
    weight: float = 1.0


DIMENSIONS: tuple[Dimension, ...] = (
    Dimension("directory_organization", "Directory organization", (
        Check("frontend_root", "Frontend is isolated under apps/web.", "apps/web"),
        Check("service_roots", "Deployable service roots are present.", "services/layer*-*", glob=True),
        Check("contract_root", "Contract source of truth exists.", "contracts"),
        Check("runtime_path_governance", "Canonical runtime path governance is documented.",
              "docs/reference/layer-runtime-path-governance.md"),
    )),
    Dimension("ci_cd_coverage", "CI/CD coverage", (
        Check("pr_checks", "Primary PR checks workflow exists.", ".github/workflows/pr-checks.yml"),
        Check("structural_preflight", "Structural preflight is enforced in PR checks.",
              ".github/workflows/pr-checks.yml", "structural-preflight"),
        Check("contract_compliance", "Contract compliance workflow exists.",
              ".github/workflows/contract-compliance.yml", "contract-scorecard"),
        Check("prod_readiness", "Production readiness workflow exists.",
              ".github/workflows/prod-readiness.yml", "gate-release-policy"),
    )),
    Dimension("docker_containerization", "Docker/containerization", (
        Check("dev_compose", "Development compose stack exists.", "docker-compose.dev.yml"),
        Check("full_compose", "Full-stack compose definition exists.", "docker-compose.full.yml"),
        Check("service_dockerfiles", "Service Dockerfiles are present.", "services/**/Dockerfile*", glob=True),
        Check("k8s_manifests", "Kubernetes manifests are present.", "k8s"),
    )),
    Dimension("testing_infrastructure", "Testing infrastructure", (
        Check("pytest_config", "Pytest configuration defines shared markers.", "pytest.ini"),
        Check("security_tests", "Security test suite exists.", "tests/security"),
        Check("contract_tests", "Contract test suite exists.", "tests/contract"),
        Check("frontend_tests", "Frontend package exposes test scripts.", "apps/web/package.json", "test"),
        Check("backend_integrated_tests", "Backend-integrated test suite exists.", "tests/backend_integrated"),
    )),
    Dimension("configuration_management", "Configuration management", (
        Check("env_example", "Safe environment template exists.", ".env.example"),
        Check("prod_gate_policy", "Production gate policy exists.", ".fabric/prod-gates.policy.yaml"),
        Check("ci_config", "CI policy config directory exists.", "config/ci"),
        Check("external_secrets", "ExternalSecret manifests are present.",
              "k8s/**/externalsecret*.yaml", glob=True),
    )),
    Dimension("observability", "Observability", (
        Check("monitoring_root", "Monitoring assets exist.", "monitoring"),
        Check("slo_contract", "SLO contract is documented.", "docs/slo/performance-slo.v1.json"),
        Check("obs_gate", "Production readiness workflow includes observability gate.",
              ".github/workflows/prod-readiness.yml", "gate-obs"),
        Check("observability_evidence", "Observability deployment readiness evidence exists.",
              "docs/readiness/observability-deployment-readiness.md"),
    )),
    Dimension("script_availability", "Script availability", (
        Check("make_verify", "Makefile exposes verify target.", "Makefile", "verify:"),
        Check("release_gate_script", "Release gate script exists.", "scripts/ops/release-gate.sh"),
        Check("zero_trust_script", "Zero-trust validation script exists.",
              "scripts/security/zero_trust_checks.sh"),
        Check("aggregate_checks", "Root aggregate check runner exists.",
              "scripts/ci/run_root_aggregate_checks.py"),
    )),
    Dimension("documentation", "Documentation", (
        Check("docs_index", "Documentation index exists.", "docs/README.md"),
        Check("frontend_governance", "Frontend governance contract exists.", "DESIGN.md"),
        Check("production_checklist", "Production readiness checklist exists.",
              "docs/PRODUCTION_READINESS_CHECKLIST.md"),
        Check("runbook_index", "Runbook index exists.", "docs/runbooks/00-runbook-index.md"),
    )),
    Dimension("security_posture", "Security posture", (
        Check("security_doc", "Security policy documentation exists.", "SECURITY.md"),
        Check("critical_gates", "Critical security gates workflow exists.", ".github/workflows/critical-gates.yml"),
        Check("security_workflow", "Security validation workflow exists.", ".github/workflows/security-validation.yml"),
        Check("tenant_security_tests", "Tenant isolation tests exist.", "tests/security", "tenant"),
        Check("zero_trust_validation", "Zero-trust validation script exists.",
              "scripts/security/zero_trust_checks.sh"),
    )),
    Dimension("contract_governance", "Contract governance", (
        Check("contracts_root", "Contracts directory exists.", "contracts"),
        Check("contract_governance_doc", "Contract governance documentation exists.", "contracts/GOVERNANCE.md"),
        Check("openapi_contracts", "OpenAPI contracts exist.", "contracts/openapi", required=False),
        Check("contract_scorecard_ci", "Contract scorecard runs in CI.",
              ".github/workflows/contract-compliance.yml", "contract-scorecard"),
        Check("contract_tests", "Contract tests exist.", "tests/contract"),
    )),
    Dimension("release_readiness", "Release readiness", (
        Check("prod_readiness_workflow", "Production readiness workflow exists.",
              ".github/workflows/prod-readiness.yml"),
        Check("release_gate", "Production readiness workflow invokes release policy gate.",
              ".github/workflows/prod-readiness.yml", "gate-release-policy"),
        Check("launch_runbook", "Launch runbook exists.", "docs/LAUNCH_RUNBOOK.md"),
        Check("release_evidence_bundle", "Release evidence bundle workflow exists.",
              ".github/workflows/release-evidence-bundle.yml"),
        Check("readiness_checklist", "Production readiness checklist exists.",
              "docs/PRODUCTION_READINESS_CHECKLIST.md"),
    )),
)

AUTOMATION_GATES: tuple[Check, ...] = (
    Check("make_verify", "Makefile exposes the canonical verify target.", "Makefile", "verify:"),
    Check("prod_readiness_workflow", "Production readiness workflow exists.", ".github/workflows/prod-readiness.yml"),
    Check("critical_security_workflow", "Critical P0 security workflow exists.",
          ".github/workflows/critical-gates.yml"),
    Check("contract_scorecard_ci", "Contract scorecard automation is present in CI.",
          ".github/workflows/contract-compliance.yml", "contract-scorecard"),
    Check("tenant_isolation_gate", "Tenant isolation gate participates in PR readiness.",
          ".github/workflows/pr-checks.yml", "tenant-isolation-gate"),
    Check("release_gate_script", "Canonical release gate script exists.", "scripts/ops/release-gate.sh"),
    Check("release_policy_gate", "Production readiness workflow invokes the release policy gate.",
          ".github/workflows/prod-readiness.yml", "gate-release-policy"),
)

SOURCE_REPORTS = (
    "docs/PRODUCTION_READINESS_CHECKLIST.md",
    "docs/governance/production-readiness-p0-foundations.md",
    "docs/readiness/observability-deployment-readiness.md",
    "docs/audit/production-readiness-2026-05-27.md",
    "reports/production-launch-readiness-audit.md",
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line(path: Path, needle: str | None = None) -> int | None:
    if not path.exists() or not path.is_file():
        return None
    if not needle:
        return 1
    lowered = needle.lower()
    for index, line in enumerate(_read(path).splitlines(), start=1):
        if lowered in line.lower():
            return index
    return None


def _matches(root: Path, check: Check) -> list[Path]:
    if check.glob:
        return sorted(path for path in root.glob(check.path) if path.exists())
    path = root / check.path
    return [path] if path.exists() else []


def _evaluate(root: Path, check: Check) -> tuple[bool, dict[str, Any] | None]:
    for path in _matches(root, check):
        if check.contains and path.is_file() and check.contains.lower() not in _read(path).lower():
            continue
        item: dict[str, Any] = {
            "path": path.relative_to(root).as_posix(),
            "description": check.description,
            "check": check.key,
        }
        line = _line(path, check.contains)
        if line is not None:
            item["line"] = line
        return True, item
    return False, None


def _dimensions(root: Path) -> list[dict[str, Any]]:
    scored = []
    for dimension in DIMENSIONS:
        evidence = []
        missing = []
        required = [check for check in dimension.checks if check.required]
        passed = 0
        for check in dimension.checks:
            ok, item = _evaluate(root, check)
            if ok and item:
                evidence.append(item)
                passed += int(check.required)
            elif check.required:
                missing.append(check.key)
        score = round((passed / len(required)) * MAX_SCORE, 1) if required else MAX_SCORE
        scored.append({
            "id": dimension.key,
            "name": dimension.name,
            "score": score,
            "max_score": MAX_SCORE,
            "status": "pass" if not missing else "fail" if not evidence else "partial",
            "weight": dimension.weight,
            "evidence": evidence,
            "missing_required_evidence": missing,
        })
    return scored


def _cell(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _checklist_p0_gates(root: Path) -> list[dict[str, Any]]:
    path = root / "docs/PRODUCTION_READINESS_CHECKLIST.md"
    if not path.exists():
        return [{
            "id": "production_readiness_checklist",
            "name": "Production readiness checklist",
            "source": "docs/PRODUCTION_READINESS_CHECKLIST.md",
            "line": None,
            "status": "missing",
            "priority": "P0",
            "description": "Production readiness checklist is missing.",
        }]
    gates = []
    for line_no, line in enumerate(_read(path).splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or "|---" in stripped or "| # |" in stripped:
            continue
        cells = [_cell(cell) for cell in stripped.strip("|").split("|")]
        if len(cells) < 5 or cells[3] != "P0":
            continue
        status_text = cells[4].upper()
        status = "fail" if "FAIL" in status_text else "partial" if "PARTIAL" in status_text else "unknown"
        if "PASS" in status_text and status == "unknown":
            status = "pass"
        gates.append({
            "id": cells[0],
            "name": cells[1],
            "source": "docs/PRODUCTION_READINESS_CHECKLIST.md",
            "line": line_no,
            "status": status,
            "priority": "P0",
            "description": cells[2],
        })
    return gates


def _automation_gates(root: Path) -> list[dict[str, Any]]:
    gates = []
    for check in AUTOMATION_GATES:
        ok, evidence = _evaluate(root, check)
        gates.append({
            "id": check.key,
            "name": check.description,
            "source": evidence["path"] if evidence else check.path,
            "line": evidence.get("line") if evidence else None,
            "status": "pass" if ok else "missing",
            "priority": "P0",
            "description": check.description,
        })
    return gates


def _required_checks(gates: list[dict[str, Any]], dimensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [
        {
            "id": gate["id"],
            "status": "pass" if gate["status"] == "pass" else "fail",
            "source": gate["source"],
            "line": gate.get("line"),
            "description": gate["description"],
        }
        for gate in gates
    ]
    checks.extend(
        {
            "id": f"dimension:{dimension['id']}",
            "status": "pass" if dimension["status"] == "pass" else "fail",
            "source": DEFAULT_OUTPUT,
            "line": None,
            "description": f"{dimension['name']} required evidence complete.",
        }
        for dimension in dimensions
    )
    return checks


def compute_scorecard(root: Path = ROOT) -> dict[str, Any]:
    dimensions = _dimensions(root)
    p0_gates = _checklist_p0_gates(root) + _automation_gates(root)
    weighted = sum(dimension["score"] * dimension["weight"] for dimension in dimensions)
    weight = sum(dimension["weight"] for dimension in dimensions)
    raw_score = round(weighted / weight, 1) if weight else 0.0
    p0_failures = [gate for gate in p0_gates if gate["status"] != "pass"]
    dimension_failures = [dimension for dimension in dimensions if dimension["status"] != "pass"]
    overall_score = min(raw_score, P0_FAILURE_SCORE_CAP) if p0_failures else raw_score
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if not p0_failures and not dimension_failures and overall_score == MAX_SCORE else "fail",
        "overall_score": overall_score,
        "max_score": MAX_SCORE,
        "dimensions": dimensions,
        "p0_gates": p0_gates,
        "required_checks": _required_checks(p0_gates, dimensions),
        "source_reports": [
            {"path": report, "present": (root / report).exists(), "line": 1 if (root / report).exists() else None}
            for report in SOURCE_REPORTS
        ],
    }


def validate_scorecard_shape(report: dict[str, Any]) -> list[str]:
    errors = []
    top_level = {
        "schema_version", "generated_at", "status", "overall_score", "max_score",
        "dimensions", "p0_gates", "required_checks", "source_reports",
    }
    missing = sorted(top_level - set(report))
    if missing:
        errors.append(f"Missing top-level fields: {', '.join(missing)}")
    if not isinstance(report.get("dimensions"), list) or len(report.get("dimensions", [])) != len(DIMENSIONS):
        errors.append("Dimensions must be a list containing every configured dimension.")
    for dimension in report.get("dimensions", []):
        required = {"id", "name", "score", "max_score", "status", "weight", "evidence", "missing_required_evidence"}
        missing_fields = sorted(required - set(dimension))
        if missing_fields:
            errors.append(f"Dimension {dimension.get('id', '<unknown>')} missing: {', '.join(missing_fields)}")
        if not dimension.get("evidence"):
            errors.append(f"Dimension {dimension.get('id', '<unknown>')} has no evidence links.")
    return errors


def _load_readiness_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _readiness_results(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    results = summary.get("results")
    if not isinstance(results, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for result in results:
        if isinstance(result, dict) and isinstance(result.get("key"), str):
            out[result["key"]] = result
    return out


def _package_script_regression(root: Path) -> dict[str, Any]:
    package_path = root / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - scorecard should report concise failures.
        return {"id": "required_package_scripts", "status": "fail", "description": f"failed to read package.json: {exc}"}

    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        return {"id": "required_package_scripts", "status": "fail", "description": "package.json scripts must be an object"}

    failures = [
        f"{name}: expected {expected!r}, got {scripts.get(name)!r}"
        for name, expected in REQUIRED_PACKAGE_SCRIPTS.items()
        if scripts.get(name) != expected
    ]
    return {
        "id": "required_package_scripts",
        "status": "fail" if failures else "pass",
        "description": "; ".join(failures) if failures else "required root package scripts match",
    }


def _readiness_workflow_regressions(root: Path) -> list[dict[str, Any]]:
    workflow = root / ".github" / "workflows" / "launch-readiness.yml"
    if not workflow.exists():
        return [{"id": "launch_readiness_workflow", "status": "fail", "description": "launch-readiness workflow is missing"}]
    text = workflow.read_text(encoding="utf-8")
    checks = (
        ("launch_readiness_runs_readiness_10", "pnpm readiness:10" in text, "launch-readiness workflow runs pnpm readiness:10"),
        ("launch_readiness_uploads_readiness_artifacts", "artifacts/readiness-10/**" in text, "launch-readiness workflow uploads readiness artifacts"),
        ("launch_readiness_gate_is_blocking", "pnpm readiness:10 || true" not in text and "pnpm readiness:10 ||" not in text, "readiness:10 is not guarded by || true"),
    )
    return [
        {"id": key, "status": "pass" if ok else "fail", "description": detail}
        for key, ok, detail in checks
    ]


def _readiness_script_regressions(root: Path) -> list[dict[str, Any]]:
    paths = (
        root / "scripts" / "ci" / "readiness_10_gate.py",
        root / "scripts" / "reports" / "generate_repo_maturity_scorecard.py",
    )
    return [
        {
            "id": f"required_file_{path.stem}",
            "status": "pass" if path.exists() else "fail",
            "description": f"{path.relative_to(root).as_posix()} {'exists' if path.exists() else 'is missing'}",
        }
        for path in paths
    ]


def _readiness_regressions(root: Path = ROOT) -> list[dict[str, Any]]:
    return [_package_script_regression(root), *_readiness_workflow_regressions(root), *_readiness_script_regressions(root)]


def build_readiness_threshold_scorecard(
    readiness_summary: dict[str, Any],
    *,
    min_score: float,
    root: Path = ROOT,
) -> dict[str, Any]:
    by_key = _readiness_results(readiness_summary)
    dimensions: list[dict[str, Any]] = []
    for key in READINESS_DIMENSION_KEYS:
        result = by_key.get(key)
        if result is None:
            dimensions.append({"id": key, "status": "fail", "score": 0.0, "description": "readiness gate result missing"})
            continue
        passed = result.get("status") == "passed"
        dimensions.append({
            "id": key,
            "status": "pass" if passed else "fail",
            "score": 1.0 if passed else 0.0,
            "description": str(result.get("summary") or result.get("status") or ""),
        })

    regressions = _readiness_regressions(root)
    regression_failures = [check for check in regressions if check["status"] != "pass"]
    dimensions.append({
        "id": "p0_maturity_ticket_regressions",
        "status": "fail" if regression_failures else "pass",
        "score": 0.0 if regression_failures else 1.0,
        "description": (
            "; ".join(f"{check['id']}: {check['description']}" for check in regression_failures)
            if regression_failures
            else "no P0 maturity ticket regressions detected"
        ),
    })

    overall_score = round(sum(float(dimension["score"]) for dimension in dimensions), 2)
    failures = [
        f"{dimension['id']}: {dimension['description']}"
        for dimension in dimensions
        if dimension["status"] != "pass"
    ]
    if overall_score < min_score:
        failures.append(f"maturity score {overall_score}/10 is below required {min_score:g}/10")

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if not failures else "fail",
        "overall_score": overall_score,
        "max_score": MAX_SCORE,
        "min_score": min_score,
        "dimensions": dimensions,
        "p0_gates": regressions,
        "required_checks": [
            {
                "id": dimension["id"],
                "status": dimension["status"],
                "source": "artifacts/readiness-10/readiness-10-summary.json",
                "line": None,
                "description": dimension["description"],
            }
            for dimension in dimensions
        ],
        "source_reports": [{"path": "artifacts/readiness-10/readiness-10-summary.json", "present": bool(by_key), "line": 1 if by_key else None}],
        "failure_summary": failures,
    }


def render_readiness_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Repository Maturity Scorecard",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Score: **{report['overall_score']}/10**",
        f"- Required score: **{report['min_score']}/10**",
        f"- Status: **{report['status'].upper()}**",
        "",
        "| Dimension | Status | Points | Detail |",
        "|---|---|---:|---|",
    ]
    for dimension in report["dimensions"]:
        status = "PASS" if dimension["status"] == "pass" else "FAIL"
        lines.append(f"| {dimension['id']} | {status} | {dimension['score']} | {dimension['description']} |")
    lines.extend(["", "## P0 Regression Checks", "", "| Check | Status | Detail |", "|---|---|---|"])
    for gate in report["p0_gates"]:
        status = "PASS" if gate["status"] == "pass" else "FAIL"
        lines.append(f"| {gate['id']} | {status} | {gate['description']} |")
    if report.get("failure_summary"):
        lines.extend(["", "## Failure Summary", ""])
        for failure in report["failure_summary"]:
            lines.append(f"- {failure}")
    lines.append("")
    return "\n".join(lines)


def write_scorecard(report: dict[str, Any], output: Path) -> None:
    if output.suffix.lower() == ".json":
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return
    output.mkdir(parents=True, exist_ok=True)
    (output / SCORECARD_JSON).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / SCORECARD_MD).write_text(render_readiness_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--no-fail", action="store_true", help="Write scorecard even when readiness fails")
    parser.add_argument("--min-score", type=float, default=None, help="Fail unless the readiness threshold score reaches this value out of 10")
    parser.add_argument("--readiness-summary", type=Path, default=DEFAULT_READINESS_SUMMARY)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args(argv)
    if args.min_score is not None:
        readiness_summary = args.readiness_summary if args.readiness_summary.is_absolute() else ROOT / args.readiness_summary
        artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else ROOT / args.artifact_dir
        report = build_readiness_threshold_scorecard(
            _load_readiness_summary(readiness_summary),
            min_score=args.min_score,
            root=ROOT,
        )
        write_scorecard(report, artifact_dir)
        print(render_readiness_markdown(report))
        return 0 if args.no_fail or report["status"] == "pass" else 1

    report = compute_scorecard(ROOT)
    write_scorecard(report, ROOT / args.output)
    errors = validate_scorecard_shape(report)
    if errors:
        for error in errors:
            print(f"schema validation error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if args.no_fail or report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
