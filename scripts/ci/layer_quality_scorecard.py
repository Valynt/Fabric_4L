#!/usr/bin/env python3
"""Generate per-layer quality scorecard and enforce regression threshold policy."""
from __future__ import annotations
import argparse, json
from dataclasses import dataclass
from datetime import UTC, datetime
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


def compute(policy: dict) -> dict:
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
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy_version": policy["version"],
        "thresholds": policy["thresholds"],
        "overall_score": overall,
        "failed_layers": failed_layers,
        "status": "pass" if len(failed_layers) <= max_fail else "fail",
        "layers": per_layer,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="docs/governance/layer-quality-threshold-policy.json")
    ap.add_argument("--output", default="docs/governance/layer-quality-scorecard.json")
    ap.add_argument("--summary", default="artifacts/layer-quality-scorecard.md")
    args = ap.parse_args()
    policy = json.loads((ROOT / args.policy).read_text(encoding="utf-8"))
    report = compute(policy)
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
        emoji = "✅" if data["status"] == "pass" else "❌"
        lines.append(
            f"| {layer} | {data['score']} | {data['passed_checks']}/{data['total_checks']} | {emoji} {data['status']} |"
        )
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1

if __name__ == "__main__":
    raise SystemExit(main())
