#!/usr/bin/env python3
"""Validate gate registry and contract inventory, and generate release-readiness reports.

This script is the enforcement engine for the Fabric_4L gate-engineering framework.
It validates:
  - gate-registry.json against gate-schema.json
  - contract-inventory.json against contract-schema.json
  - cross-references between gates and contracts
  - a release-readiness report from gate result evidence

Exit codes:
  0 = all validations passed
  1 = validation error or blocked release
  2 = bad arguments
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
GATE_ENGINEERING_DIR = ROOT / ".fabric" / "gate-engineering"
GATE_SCHEMA = GATE_ENGINEERING_DIR / "gate-schema.json"
GATE_REGISTRY = GATE_ENGINEERING_DIR / "gate-registry.json"
CONTRACT_SCHEMA = GATE_ENGINEERING_DIR / "contract-schema.json"
CONTRACT_INVENTORY = GATE_ENGINEERING_DIR / "contract-inventory.json"

DEFAULT_ARTIFACT_DIR = ROOT / "artifacts" / "release"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _validate_schema(instance: Any, schema: dict[str, Any], path: Path, context: str = "") -> list[str]:
    errors: list[str] = []
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError as exc:
        prefix = f"{path}: {context}" if context else f"{path}"
        errors.append(f"{prefix}: {exc.message} at {list(exc.path)}")
    return errors


def _validate_gate_registry(registry: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for idx, gate in enumerate(registry.get("gates", [])):
        errors.extend(_validate_schema(gate, schema, GATE_REGISTRY, f"gates[{idx}]"))
    gate_ids = [g["gate_id"] for g in registry.get("gates", [])]
    duplicates = {gid for gid in gate_ids if gate_ids.count(gid) > 1}
    if duplicates:
        errors.append(f"duplicate gate_id values: {duplicates}")
    return errors


def _validate_contract_inventory(inventory: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for idx, contract in enumerate(inventory.get("contracts", [])):
        errors.extend(_validate_schema(contract, schema, CONTRACT_INVENTORY, f"contracts[{idx}]"))
    contract_ids = [c["contract_id"] for c in inventory.get("contracts", [])]
    duplicates = {cid for cid in contract_ids if contract_ids.count(cid) > 1}
    if duplicates:
        errors.append(f"duplicate contract_id values: {duplicates}")
    return errors


def _validate_cross_references(registry: dict[str, Any], inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract_ids = {c["contract_id"] for c in inventory.get("contracts", [])}
    for gate in registry.get("gates", []):
        for related in gate.get("related_contracts", []):
            if related not in contract_ids:
                errors.append(
                    f"gate {gate['gate_id']} references unknown contract {related}"
                )
    return errors


def _summarize_gate(registry_gate: dict[str, Any], result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "gate_id": registry_gate["gate_id"],
            "name": registry_gate["name"],
            "result": "INCONCLUSIVE",
            "reason": "no evidence submitted",
            "owner": registry_gate["owner"],
            "criticality": registry_gate["criticality"],
        }
    status = result.get("status", "INCONCLUSIVE")
    return {
        "gate_id": registry_gate["gate_id"],
        "name": registry_gate["name"],
        "result": status,
        "reason": result.get("reason", ""),
        "evidence_uri": result.get("evidence_uri", ""),
        "owner": registry_gate["owner"],
        "criticality": registry_gate["criticality"],
    }


def _load_results(artifact_dir: Path) -> dict[str, dict[str, Any]]:
    """Load gate results from JSON files in artifact_dir matching gate-*.json."""
    results: dict[str, dict[str, Any]] = {}
    if not artifact_dir.exists():
        return results
    for path in artifact_dir.glob("gate-*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "gate_id" in data:
            results[data["gate_id"]] = data
    return results


def _build_release_readiness_report(
    registry: dict[str, Any],
    results: dict[str, dict[str, Any]],
    *,
    release_id: str,
    artifact_digest: str,
    commit_sha: str,
    environment: str,
    risk_class: str,
) -> dict[str, Any]:
    status_to_key = {
        "PASS": "passed",
        "FAIL": "failed",
        "INCONCLUSIVE": "inconclusive",
        "NOT_APPLICABLE": "not_applicable",
        "WARNING": "warnings",
    }
    summary: dict[str, int] = {
        "passed": 0,
        "failed": 0,
        "inconclusive": 0,
        "not_applicable": 0,
        "warnings": 0,
    }
    blocking_results: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for gate in registry.get("gates", []):
        result = _summarize_gate(gate, results.get(gate["gate_id"]))
        status = result["result"]
        key = status_to_key.get(status, status.lower())
        summary[key] = summary.get(key, 0) + 1

        if status == "FAIL" and gate["criticality"] == "blocking":
            blocking_results.append(
                {
                    "gate_id": gate["gate_id"],
                    "result": status,
                    "criterion": gate["fail_criteria"][0],
                    "evidence_uri": result.get("evidence_uri", ""),
                    "owner": gate["owner"],
                }
            )
        elif status == "INCONCLUSIVE" and gate["criticality"] == "blocking":
            blocking_results.append(
                {
                    "gate_id": gate["gate_id"],
                    "result": status,
                    "criterion": gate["inconclusive_criteria"][0],
                    "evidence_uri": result.get("evidence_uri", ""),
                    "owner": gate["owner"],
                }
            )
        elif status == "WARNING":
            warnings.append(result)

    decision = "blocked" if blocking_results else "ready"
    if risk_class == "emergency" and not any(
        r["gate_id"].startswith("pre_production.tenant_isolation")
        or r["gate_id"].startswith("security.p0_auth_boundaries")
        for r in blocking_results
    ):
        # Even emergency releases cannot bypass tenant isolation or auth.
        decision = "blocked" if blocking_results else "ready-with-exception-review"

    return {
        "release_id": release_id,
        "artifact_digest": artifact_digest,
        "commit_sha": commit_sha,
        "environment": environment,
        "risk_class": risk_class,
        "decision": decision,
        "gates": summary,
        "blocking_results": blocking_results,
        "warnings": warnings,
        "exceptions": [],
        "generated_at": _utc_now(),
        "evidence_expiration": "24h",
        "schema": "https://valuefabric.ai/fabric/gate-engineering/gate-schema.json",
    }


def _render_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Release Readiness Report",
        "",
        f"- **Release ID:** `{report['release_id']}`",
        f"- **Artifact digest:** `{report['artifact_digest']}`",
        f"- **Commit SHA:** `{report['commit_sha']}`",
        f"- **Environment:** `{report['environment']}`",
        f"- **Risk class:** `{report['risk_class']}`",
        f"- **Decision:** `{report['decision']}`",
        f"- **Generated at:** `{report['generated_at']}`",
        "",
        "## Gate summary",
        "",
        f"- **PASS:** {report['gates']['passed']}",
        f"- **FAIL:** {report['gates']['failed']}",
        f"- **INCONCLUSIVE:** {report['gates']['inconclusive']}",
        f"- **NOT_APPLICABLE:** {report['gates']['not_applicable']}",
        f"- **WARNING:** {report['gates']['warnings']}",
        "",
    ]
    if report["blocking_results"]:
        lines.append("## Blocking results")
        lines.append("")
        for r in report["blocking_results"]:
            lines.append(
                f"- `{r['gate_id']}` — `{r['result']}` — {r['criterion']} (owner: {r['owner']})"
            )
        lines.append("")
    if report["warnings"]:
        lines.append("## Warnings")
        lines.append("")
        for w in report["warnings"]:
            lines.append(f"- `{w['gate_id']}` — {w['reason']}")
        lines.append("")
    lines.append("This report is generated from authoritative gate results. Manual edits are not allowed.")
    return "\n".join(lines)


def validate(args: argparse.Namespace) -> int:
    schema = _load_json(GATE_SCHEMA)
    registry = _load_json(GATE_REGISTRY)
    contract_schema = _load_json(CONTRACT_SCHEMA)
    inventory = _load_json(CONTRACT_INVENTORY)

    errors: list[str] = []
    errors.extend(_validate_gate_registry(registry, schema))
    errors.extend(_validate_contract_inventory(inventory, contract_schema))
    errors.extend(_validate_cross_references(registry, inventory))

    if errors:
        print("Validation failed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("Validation passed.")
    print(f"  Gates: {len(registry.get('gates', []))}")
    print(f"  Contracts: {len(inventory.get('contracts', []))}")
    return 0


def report(args: argparse.Namespace) -> int:
    registry = _load_json(GATE_REGISTRY)
    results = _load_results(Path(args.artifact_dir))
    report_data = _build_release_readiness_report(
        registry,
        results,
        release_id=args.release_id,
        artifact_digest=args.artifact_digest,
        commit_sha=args.commit_sha,
        environment=args.environment,
        risk_class=args.risk_class,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "release-readiness-report.json"
    md_path = output_dir / "release-readiness-report.md"
    json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    md_path.write_text(_render_report_markdown(report_data), encoding="utf-8")

    print(f"Report written to {output_dir}")
    print(f"  Decision: {report_data['decision']}")
    print(f"  Blocking: {len(report_data['blocking_results'])}")
    return 0 if report_data["decision"] in ("ready", "ready-with-exception-review") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fabric_4L gate engineering validator")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate", help="Validate registry and inventory schemas")
    validate_cmd.set_defaults(func=validate)

    report_cmd = sub.add_parser("report", help="Generate a release-readiness report")
    report_cmd.add_argument("--release-id", required=True)
    report_cmd.add_argument("--artifact-digest", required=True)
    report_cmd.add_argument("--commit-sha", required=True)
    report_cmd.add_argument("--environment", default="production")
    report_cmd.add_argument("--risk-class", default="high")
    report_cmd.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    report_cmd.add_argument("--output-dir", default=str(DEFAULT_ARTIFACT_DIR))
    report_cmd.set_defaults(func=report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
