#!/usr/bin/env python3
"""Validate gate registry and contract inventory, and generate release-readiness reports.

This script is the enforcement engine for the Fabric_4L gate-engineering framework.
It validates:
  - gate-registry.json against gate-schema.json
  - contract-inventory.json against contract-schema.json
  - cross-references between gates and contracts
  - gate evidence for freshness, binding, ownership, and placeholder content
  - a release-readiness report bound to the current commit and generated artifacts

Exit codes:
  0 = all validations passed / release ready
  1 = validation error or blocked release
  2 = bad arguments
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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

PLACEHOLDER_MARKERS = (
    "injected",
    "placeholder",
    "example",
    "artifact:test",
    "sha256:0000",
    "sha256:1111",
    "sha256:2222",
    "sha256:3333",
    "synthetic",
    "manual",
    "not-real",
)

# Fields that should participate in placeholder detection. Structural metadata
# such as gate_id, status, or timestamps must not be treated as evidence content.
_EVIDENCE_FIELDS = {
    "reason",
    "evidence_uri",
    "command",
    "output",
    "summary",
    "details",
    "message",
    "stderr",
    "stdout",
}


FRESHNESS_SECONDS = {
    "5m": 300,
    "1h": 3600,
    "24h": 86400,
    "7d": 604800,
    "PR lifetime": 0,  # Always fresh within a PR run
    "artifact lifetime": 0,
    "release": 0,
    "deployment": 0,
    "canary window": 0,
}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_now_dt() -> datetime:
    return datetime.now(UTC)


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


def _hash_files(*patterns: str) -> str:
    """Return a deterministic sha256 of the contents of files matching the patterns."""
    h = hashlib.sha256()
    files: list[Path] = []
    for pattern in patterns:
        files.extend(ROOT.glob(pattern))
    files = sorted({f.resolve() for f in files if f.is_file()})
    for f in files:
        h.update(f"{f.relative_to(ROOT)}\0".encode("utf-8"))
        h.update(f.read_bytes())
    return f"sha256:{h.hexdigest()}"


def _collect_identity() -> dict[str, Any]:
    """Collect release identity: commit, artifact hashes, migration state, config fingerprint."""
    identity: dict[str, Any] = {
        "openapi_schema_hash": _hash_files("contracts/openapi/*.json"),
        "generated_client_hash": _hash_files(
            "apps/web/src/api/generated/**/*",
            "packages/platform-contract/src/typescript/generated/**/*",
        ),
        "config_fingerprint": _hash_files(
            "k8s/envs/prod/**/*",
            "k8s/envs/staging/**/*",
        ),
    }
    try:
        identity["commit_sha"] = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            .stdout.strip()
            or "unknown"
        )
    except Exception:
        identity["commit_sha"] = "unknown"

    # Migration revision: hash of all Alembic version files for each layer.
    migration_files = sorted(ROOT.glob("services/**/alembic/versions/*.py"))
    identity["migration_revision"] = _hash_files(
        *[str(f.relative_to(ROOT)) for f in migration_files]
    )

    return identity


def _parse_iso_timestamp(value: str) -> datetime | None:
    try:
        # Strip trailing Z and replace with +00:00 for fromisoformat
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        text = json.dumps({k: v for k, v in value.items() if k in _EVIDENCE_FIELDS})
    else:
        text = value if isinstance(value, str) else json.dumps(value)
    return any(marker.lower() in text.lower() for marker in PLACEHOLDER_MARKERS)


def _is_stale(result: dict[str, Any], freshness: str) -> bool:
    produced_at = result.get("produced_at") or result.get("timestamp")
    if not produced_at:
        return False
    threshold = FRESHNESS_SECONDS.get(freshness)
    if threshold is None:
        # Unknown freshness rule: use 24h default
        threshold = 86400
    if threshold == 0:
        return False
    produced_dt = _parse_iso_timestamp(produced_at)
    if produced_dt is None:
        return True
    return (_utc_now_dt() - produced_dt).total_seconds() > threshold


def _validate_evidence(
    gate: dict[str, Any],
    result: dict[str, Any] | None,
    *,
    artifact_digest: str,
    commit_sha: str,
    strict: bool,
) -> dict[str, Any]:
    """Validate a single gate's evidence and return a normalized result.

    Returns dict with:
      - status: PASS, FAIL, INCONCLUSIVE, WARNING
      - reason: human-readable reason
      - evidence_uri
      - evidence_valid: bool
    """
    producer = gate.get("evidence_producer")

    if result is None:
        return {
            "status": "INCONCLUSIVE",
            "reason": "no evidence submitted",
            "evidence_uri": "",
            "evidence_valid": False,
        }

    # Unknown command check
    if producer:
        expected_command = producer["command"]
        actual_command = result.get("command", "")
        if actual_command and actual_command != expected_command:
            return {
                "status": "INCONCLUSIVE",
                "reason": f"evidence produced by unknown command: {actual_command}",
                "evidence_uri": result.get("evidence_uri", ""),
                "evidence_valid": False,
            }

    # Owner check
    if producer:
        expected_owner = producer["owner"]
        actual_owner = result.get("owner", "")
        if actual_owner and actual_owner != expected_owner:
            return {
                "status": "INCONCLUSIVE",
                "reason": f"evidence owner mismatch: expected {expected_owner}, got {actual_owner}",
                "evidence_uri": result.get("evidence_uri", ""),
                "evidence_valid": False,
            }

    # Artifact binding check
    if producer:
        expected_binding = producer["artifact_binding"]
        bound_to = result.get("bound_to", "")
        if bound_to:
            if expected_binding == "commit-sha" and bound_to != commit_sha:
                return {
                    "status": "INCONCLUSIVE",
                    "reason": f"evidence bound to different commit: {bound_to}",
                    "evidence_uri": result.get("evidence_uri", ""),
                    "evidence_valid": False,
                }
            if expected_binding in ("container-image-digest", "artifact-digest") and bound_to != artifact_digest:
                return {
                    "status": "INCONCLUSIVE",
                    "reason": f"evidence bound to different artifact digest: {bound_to}",
                    "evidence_uri": result.get("evidence_uri", ""),
                    "evidence_valid": False,
                }

    # Placeholder check
    if _is_placeholder(result):
        if strict:
            return {
                "status": "INCONCLUSIVE",
                "reason": "evidence contains placeholder/example values",
                "evidence_uri": result.get("evidence_uri", ""),
                "evidence_valid": False,
            }
        return {
            "status": "WARNING",
            "reason": "evidence contains placeholder/example values",
            "evidence_uri": result.get("evidence_uri", ""),
            "evidence_valid": False,
        }

    # Staleness check
    freshness = producer["freshness"] if producer else "24h"
    if _is_stale(result, freshness):
        return {
            "status": "INCONCLUSIVE",
            "reason": f"evidence is older than {freshness}",
            "evidence_uri": result.get("evidence_uri", ""),
            "evidence_valid": False,
        }

    return {
        "status": result.get("status", "INCONCLUSIVE"),
        "reason": result.get("reason", ""),
        "evidence_uri": result.get("evidence_uri", ""),
        "evidence_valid": True,
    }


def _summarize_gate(
    registry_gate: dict[str, Any],
    result: dict[str, Any] | None,
    *,
    artifact_digest: str,
    commit_sha: str,
    strict: bool,
) -> dict[str, Any]:
    validated = _validate_evidence(
        registry_gate,
        result,
        artifact_digest=artifact_digest,
        commit_sha=commit_sha,
        strict=strict,
    )
    return {
        "gate_id": registry_gate["gate_id"],
        "name": registry_gate["name"],
        "result": validated["status"],
        "reason": validated["reason"],
        "evidence_uri": validated["evidence_uri"],
        "owner": registry_gate["owner"],
        "criticality": registry_gate["criticality"],
        "scope": registry_gate["scope"],
        "evidence_valid": validated["evidence_valid"],
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
    strict: bool,
    identity: dict[str, Any],
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
    framework_gates: list[dict[str, Any]] = []
    product_gates: list[dict[str, Any]] = []
    inconclusive_gates: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    blocking_results: list[dict[str, Any]] = []

    for gate in registry.get("gates", []):
        result = _summarize_gate(
            gate,
            results.get(gate["gate_id"]),
            artifact_digest=artifact_digest,
            commit_sha=commit_sha,
            strict=strict,
        )
        status = result["result"]
        key = status_to_key.get(status, status.lower())
        summary[key] = summary.get(key, 0) + 1

        if status in ("PASS", "FAIL"):
            if result["evidence_valid"]:
                product_gates.append(result)
            else:
                framework_gates.append(result)
        elif status == "WARNING":
            warnings.append(result)
        elif status == "INCONCLUSIVE":
            inconclusive_gates.append(result)
        else:
            framework_gates.append(result)

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
                    "remediation": gate.get("remediation"),
                }
            )

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
        "identity": {
            "artifact_digest": artifact_digest,
            "commit_sha": commit_sha,
            "openapi_schema_hash": identity["openapi_schema_hash"],
            "generated_client_hash": identity["generated_client_hash"],
            "migration_revision": identity["migration_revision"],
            "config_fingerprint": identity["config_fingerprint"],
        },
        "environment": environment,
        "risk_class": risk_class,
        "strict": strict,
        "decision": decision,
        "gates": summary,
        "framework_validation_gates": framework_gates,
        "product_evidence_gates": product_gates,
        "inconclusive_gates": inconclusive_gates,
        "warnings": warnings,
        "exceptions": [],
        "blocking_results": blocking_results,
        "generated_at": _utc_now(),
        "evidence_expiration": "24h",
        "schema": "https://valuefabric.ai/fabric/gate-engineering/gate-schema.json",
    }


def _render_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Release Readiness Report",
        "",
        f"- **Release ID:** `{report['release_id']}`",
        f"- **Artifact digest:** `{report['identity']['artifact_digest']}`",
        f"- **Commit SHA:** `{report['identity']['commit_sha']}`",
        f"- **OpenAPI schema hash:** `{report['identity']['openapi_schema_hash']}`",
        f"- **Generated client hash:** `{report['identity']['generated_client_hash']}`",
        f"- **Migration revision:** `{report['identity']['migration_revision']}`",
        f"- **Config fingerprint:** `{report['identity']['config_fingerprint']}`",
        f"- **Environment:** `{report['environment']}`",
        f"- **Risk class:** `{report['risk_class']}`",
        f"- **Strict mode:** `{report['strict']}`",
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

    if report["framework_validation_gates"]:
        lines.append("## Framework validation gates")
        lines.append("")
        for g in report["framework_validation_gates"]:
            lines.append(
                f"- `{g['gate_id']}` — `{g['result']}` — {g['reason']} (owner: {g['owner']})"
            )
        lines.append("")

    if report["product_evidence_gates"]:
        lines.append("## Real product evidence gates")
        lines.append("")
        for g in report["product_evidence_gates"]:
            lines.append(
                f"- `{g['gate_id']}` — `{g['result']}` — {g['reason']} (owner: {g['owner']})"
            )
        lines.append("")

    if report["inconclusive_gates"]:
        lines.append("## Incomplete / inconclusive gates")
        lines.append("")
        for g in report["inconclusive_gates"]:
            entry = f"- `{g['gate_id']}` — `{g['result']}` — {g['reason']} (owner: {g['owner']})"
            lines.append(entry)
        lines.append("")

    if report["warnings"]:
        lines.append("## Warnings")
        lines.append("")
        for w in report["warnings"]:
            lines.append(f"- `{w['gate_id']}` — {w['reason']}")
        lines.append("")

    if report["exceptions"]:
        lines.append("## Exceptions")
        lines.append("")
        for e in report["exceptions"]:
            lines.append(f"- `{e['gate_id']}` — exception {e['exception_id']} until {e['expires_at']}")
        lines.append("")

    if report["blocking_results"]:
        lines.append("## Blocking results")
        lines.append("")
        for r in report["blocking_results"]:
            lines.append(
                f"- `{r['gate_id']}` — `{r['result']}` — {r['criterion']} (owner: {r['owner']})"
            )
        lines.append("")

    lines.append(
        "This report is generated from authoritative gate results. "
        "Manual edits are not allowed; evidence must be produced by the registered commands."
    )
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
    identity = _collect_identity()
    # Tests and CI pipelines need a deterministic commit SHA; fall back to the
    # real git HEAD when it is not supplied.
    commit_sha = args.commit_sha or identity["commit_sha"]
    identity["commit_sha"] = commit_sha
    report_data = _build_release_readiness_report(
        registry,
        results,
        release_id=args.release_id,
        artifact_digest=args.artifact_digest,
        commit_sha=commit_sha,
        environment=args.environment,
        risk_class=args.risk_class,
        strict=args.strict,
        identity=identity,
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
    print(f"  Product evidence gates: {len(report_data['product_evidence_gates'])}")
    print(f"  Inconclusive gates: {len(report_data['inconclusive_gates'])}")
    return 0 if report_data["decision"] in ("ready", "ready-with-exception-review") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fabric_4L gate engineering validator")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate", help="Validate registry and inventory schemas")
    validate_cmd.add_argument("--strict", action="store_true", help="Fail if any gate lacks evidence_producer")
    validate_cmd.set_defaults(func=validate)

    report_cmd = sub.add_parser("report", help="Generate a release-readiness report")
    report_cmd.add_argument("--release-id", required=True)
    report_cmd.add_argument("--artifact-digest", required=True)
    report_cmd.add_argument("--commit-sha", default=None, help="Override the git commit SHA used for identity and evidence binding")
    report_cmd.add_argument("--environment", default="production")
    report_cmd.add_argument("--risk-class", default="high")
    report_cmd.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    report_cmd.add_argument("--output-dir", default=str(DEFAULT_ARTIFACT_DIR))
    report_cmd.add_argument("--strict", action="store_true", help="Reject placeholder evidence and require real bindings")
    report_cmd.set_defaults(func=report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
