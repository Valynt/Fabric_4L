#!/usr/bin/env python3
"""Generate per-layer quality scorecard and enforce regression threshold policy."""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json"}
SCOPED_SUPPORT_ROOTS = ("tests", "docs", "contracts")

LAYER_SCOPES = {
    "layer1": {
        "paths": ["value_fabric/layer1", "services/layer1-ingestion"],
        "scope_tokens": ["layer1", "ingestion"],
    },
    "layer2": {
        "paths": ["value_fabric/layer2", "services/layer2-extraction"],
        "scope_tokens": ["layer2", "extraction"],
    },
    "layer3": {
        "paths": ["value_fabric/layer3", "services/layer3-knowledge"],
        "scope_tokens": ["layer3", "knowledge", "graph"],
    },
    "layer4": {
        "paths": ["value_fabric/layer4", "services/layer4-agents"],
        "scope_tokens": ["layer4", "agents", "workflow"],
    },
    "layer5": {
        "paths": ["services/layer5-ground-truth/src/layer5_ground_truth", "services/layer5-ground-truth"],
        "scope_tokens": ["layer5", "ground-truth", "truth"],
    },
    "layer6": {
        "paths": ["value_fabric/layer6", "services/layer6-benchmarks"],
        "scope_tokens": ["layer6", "benchmark", "benchmarks"],
    },
}

@dataclass
class CheckDef:
    key: str
    description: str
    patterns: list[str]

CHECKS = [
    CheckDef("tenant_isolation_tests", "Tenant isolation test presence", ["tenant", "cross-tenant", "isolation"]),
    CheckDef("contract_tests", "Contract tests presence", ["contract", "openapi", "schema"]),
    CheckDef("migration_discipline", "Migration discipline checks", ["migration", "alembic", "revision"]),
    CheckDef("security_negative_paths", "Security/auth negative-path coverage", ["unauthorized", "forbidden", "auth", "401", "403"]),
    CheckDef("docs_contract_freshness", "Docs-contract freshness status", ["contract", "openapi", "schema", "docs"]),
]
LOWERED_CHECK_PATTERNS = {check.key: [pattern.lower() for pattern in check.patterns] for check in CHECKS}

ATTENTION_SECTIONS = ("ungoverned_hotspots", "stale_decisions", "knowledge_silos")
NORMALIZED_PATHS = {
    ".agent/harness/hooks/init.py": ".agent/harness/hooks/__init__.py",
}


def _find_any_text(paths: list[str], snippets: list[str]) -> bool:
    for rel in paths:
        p = ROOT / rel
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                continue
            if any(s in text for s in snippets):
                return True
    return False


def _find_scoped_support_text(scope_tokens: list[str], snippets: list[str]) -> bool:
    for root_name in SCOPED_SUPPORT_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for file_path in root.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel = str(file_path.relative_to(ROOT)).lower()
            if not any(token in rel for token in scope_tokens):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                continue
            if any(snippet in text for snippet in snippets):
                return True
    return False


def _path_exists(rel_path: str | None) -> bool:
    return bool(rel_path) and (ROOT / str(rel_path)).exists()


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _attention_item_status(section: str, item: dict, *, today: date) -> tuple[str, list[str]]:
    failures: list[str] = []
    original_path = item.get("path")
    normalized_path = NORMALIZED_PATHS.get(str(original_path), original_path)

    if not item.get("owner"):
        failures.append("missing owner")
    if not _path_exists(normalized_path):
        failures.append(f"missing governed path: {normalized_path}")
    if not _path_exists(item.get("evidence_path")):
        failures.append(f"missing evidence path: {item.get('evidence_path')}")
    if not item.get("remediation_state"):
        failures.append("missing remediation_state")

    review_due = _parse_iso_date(item.get("review_due") or item.get("due_date"))
    if not review_due:
        failures.append("missing or invalid review_due/due_date")
    elif review_due < today:
        failures.append(f"review_due is stale: {review_due.isoformat()}")

    if section == "ungoverned_hotspots":
        if not item.get("governing_decision"):
            failures.append("missing governing_decision")
        if item.get("generated") is True:
            if not _path_exists(item.get("source_contract")):
                failures.append(f"missing source_contract: {item.get('source_contract')}")
            if not item.get("generation_command"):
                failures.append("missing generation_command")
    elif section == "stale_decisions":
        decision_date = _parse_iso_date(item.get("decision_date"))
        if not decision_date:
            failures.append("missing or invalid decision_date")
        elif decision_date > today:
            failures.append(f"decision_date is in the future: {decision_date.isoformat()}")
        if not item.get("decision"):
            failures.append("missing decision")
        if not _path_exists(item.get("runbook_path")):
            failures.append(f"missing runbook_path: {item.get('runbook_path')}")
    elif section == "knowledge_silos":
        if not (item.get("secondary_owner") or item.get("backup_owner")):
            failures.append("missing secondary_owner or backup_owner")

    return ("pass" if not failures else "fail"), failures


def compute_attention(registry_path: str | None, *, today: date | None = None) -> dict:
    if not registry_path:
        return {"status": "pass", "sections": {section: [] for section in ATTENTION_SECTIONS}}

    registry_file = ROOT / registry_path
    if not registry_file.exists():
        return {
            "status": "fail",
            "registry": registry_path,
            "sections": {section: [] for section in ATTENTION_SECTIONS},
            "failures": [f"missing attention registry: {registry_path}"],
        }

    payload = json.loads(registry_file.read_text(encoding="utf-8"))
    current_day = today or datetime.now(UTC).date()
    sections: dict[str, list[dict]] = {}
    failed_items = 0

    for section in ATTENTION_SECTIONS:
        section_items = []
        for item in payload.get(section, []):
            status, failures = _attention_item_status(section, item, today=current_day)
            failed_items += int(status == "fail")
            original_path = item.get("path")
            normalized_path = NORMALIZED_PATHS.get(str(original_path), original_path)
            section_items.append(
                {
                    "id": item.get("id"),
                    "status": status,
                    "owner": item.get("owner"),
                    "secondary_owner": item.get("secondary_owner") or item.get("backup_owner"),
                    "path": normalized_path,
                    "reported_path": original_path,
                    "evidence_path": item.get("evidence_path"),
                    "review_due": item.get("review_due") or item.get("due_date"),
                    "remediation_state": item.get("remediation_state"),
                    "failures": failures,
                }
            )
        sections[section] = section_items

    return {
        "status": "pass" if failed_items == 0 else "fail",
        "registry": registry_path,
        "failed_items": failed_items,
        "sections": sections,
    }


def compute(policy: dict, *, attention_registry: str | None = None) -> dict:
    per_layer = {}
    for layer, scope in LAYER_SCOPES.items():
        paths = scope["paths"]
        checks = {}
        passed = 0
        for chk in CHECKS:
            lowered_patterns = LOWERED_CHECK_PATTERNS[chk.key]
            ok = _find_any_text(paths, lowered_patterns) or _find_scoped_support_text(scope["scope_tokens"], lowered_patterns)
            checks[chk.key] = {"description": chk.description, "present": ok}
            passed += int(ok)
        score = round((passed / len(CHECKS)) * 100, 1)
        min_score = policy["thresholds"]["per_layer_min_score"]
        per_layer[layer] = {
            "score": score,
            "status": "pass" if score >= min_score else "fail",
            "passed_checks": passed,
            "total_checks": len(CHECKS),
            "checks": checks,
        }

    overall = round(sum(v["score"] for v in per_layer.values()) / len(per_layer), 1)
    max_fail = policy["thresholds"]["max_failed_layers"]
    failed_layers = sorted([k for k, v in per_layer.items() if v["status"] == "fail"])
    attention = compute_attention(attention_registry)
    layer_status = "pass" if len(failed_layers) <= max_fail else "fail"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy_version": policy["version"],
        "thresholds": policy["thresholds"],
        "overall_score": overall,
        "failed_layers": failed_layers,
        "status": "pass" if layer_status == "pass" and attention["status"] == "pass" else "fail",
        "layers": per_layer,
        "attention": attention,
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="config/baselines/layer-quality-threshold-policy.json")
    ap.add_argument("--output", default="config/baselines/layer-quality-scorecard.json")
    ap.add_argument("--summary", default="artifacts/layer-quality-scorecard.md")
    ap.add_argument("--attention-registry", default="config/baselines/layer-quality-attention-registry.json")
    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    policy = json.loads((ROOT / args.policy).read_text(encoding="utf-8"))
    report = compute(policy, attention_registry=args.attention_registry)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = ROOT / args.summary
    summary.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "## Layer Quality Scorecard",
        "",
        f"Overall: **{report['overall_score']}** ({report['status']})",
        "",
        "| Layer | Score | Checks | Status |",
        "|---|---:|---:|---|",
    ]
    for layer, data in report["layers"].items():
        emoji = "PASS" if data["status"] == "pass" else "FAIL"
        lines.append(
            f"| {layer} | {data['score']} | {data['passed_checks']}/{data['total_checks']} | {emoji} {data['status']} |"
        )
    lines.extend(
        [
            "",
            "## Attention Findings",
            "",
            f"Status: **{report['attention']['status']}**",
            "",
            "| Category | ID | Path | Owner | Review Due | State | Status |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for section, items in report["attention"]["sections"].items():
        for item in items:
            label = section.replace("_", " ")
            lines.append(
                "| "
                + " | ".join(
                    [
                        label,
                        str(item.get("id") or ""),
                        str(item.get("path") or ""),
                        str(item.get("owner") or ""),
                        str(item.get("review_due") or ""),
                        str(item.get("remediation_state") or ""),
                        str(item.get("status") or ""),
                    ]
                )
                + " |"
            )
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1

if __name__ == "__main__":
    raise SystemExit(main())
