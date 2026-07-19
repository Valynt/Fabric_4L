#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None

SKIP_LINE = re.compile(r"^SKIPPED\s+\[[0-9]+\].*?:\s*(?P<reason>.+)$")

INFRA_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bdb\b|database|postgres|mysql|sqlite",
        r"\bredis\b",
        r"\bk8s\b|kubernetes|kubectl|kustomize|helm",
        r"docker|container runtime",
        r"environment variable|missing env|requires? env",
        r"external service unavailable|service unavailable",
    ]
]

VALID_CLASSIFICATIONS = {
    "valid_environment_limitation",
    "temporary_bug_waiver",
    "obsolete_test",
    "unacceptable_coverage_gap",
}

CODE_HEALTH_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"import path.*unresolved",
        r"module not found",
        r"cannot import",
        r"pending refactor",
        r"legacy import layout",
    ]
]


@dataclass
class AllowEntry:
    pattern: re.Pattern[str]
    owner: str
    expires_on: date
    classification: str
    note: str


def load_allowlist(path: Path) -> list[AllowEntry]:
    if not path.exists():
        return []
    if yaml is None:
        raise RuntimeError("pyyaml is required to parse allowlist")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("allowlist", [])
    out: list[AllowEntry] = []
    for i, entry in enumerate(entries):
        pattern = entry.get("pattern")
        owner = entry.get("owner")
        expires = entry.get("expires_on")
        classification = entry.get("classification")
        note = entry.get("note", "")
        if not pattern or not owner or not expires or not classification:
            raise ValueError(
                f"Invalid allowlist entry index {i}: pattern, owner, expires_on, classification required"
            )
        if classification not in VALID_CLASSIFICATIONS:
            raise ValueError(f"Invalid allowlist entry index {i}: unsupported classification {classification}")
        out.append(
            AllowEntry(
                re.compile(pattern, re.IGNORECASE),
                owner,
                date.fromisoformat(expires),
                classification,
                note,
            )
        )
    return out


def classify_reason(reason: str, allowlist: list[AllowEntry], today: date) -> tuple[str, str, str, str]:
    for entry in allowlist:
        if entry.pattern.search(reason):
            if entry.expires_on < today:
                return (
                    "violation",
                    "allowlisted",
                    entry.classification,
                    f"expired allowlist ({entry.owner}, expired {entry.expires_on.isoformat()})",
                )
            return (
                "allowlisted",
                "allowlisted",
                entry.classification,
                f"allowlisted by {entry.owner} until {entry.expires_on.isoformat()}",
            )

    if any(p.search(reason) for p in CODE_HEALTH_PATTERNS):
        return ("violation", "code_health", "temporary_bug_waiver", "code-health skip without allowlist owner")
    if any(p.search(reason) for p in INFRA_PATTERNS):
        return ("allowed", "infrastructure", "valid_environment_limitation", "infrastructure/environment skip")
    return ("violation", "unclassified", "unacceptable_coverage_gap", "unclassified skip reason")


def main() -> int:
    ap = argparse.ArgumentParser(description="Govern pytest skip reasons from collection output")
    ap.add_argument("collection_output", type=Path)
    ap.add_argument("--allowlist", type=Path, default=Path("config/ci/pytest_skip_allowlist.yaml"))
    ap.add_argument("--baseline", type=Path, default=Path("config/ci/pytest_skip_baseline.json"))
    ap.add_argument("--write-report", type=Path)
    args = ap.parse_args()

    content = args.collection_output.read_text(encoding="utf-8")
    reasons = [m.group("reason").strip() for line in content.splitlines() if (m := SKIP_LINE.match(line.strip()))]

    allowlist = load_allowlist(args.allowlist)
    today = date.today()

    counts: dict[str, int] = {}
    classified: list[dict[str, str]] = []
    violations: list[dict[str, str]] = []

    for reason in reasons:
        counts[reason] = counts.get(reason, 0) + 1

    category_counts = {
        "infrastructure": 0,
        "code_health": 0,
        "allowlisted": 0,
        "unclassified": 0,
    }
    classification_counts = {classification: 0 for classification in sorted(VALID_CLASSIFICATIONS)}
    unowned_skips = 0

    for reason, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        status, category, classification, detail = classify_reason(reason, allowlist, today)
        row = {
            "reason": reason,
            "count": str(count),
            "status": status,
            "category": category,
            "classification": classification,
            "detail": detail,
        }
        classified.append(row)
        category_counts[category] = category_counts.get(category, 0) + count
        classification_counts[classification] = classification_counts.get(classification, 0) + count
        if " by @" not in detail and status != "allowed":
            unowned_skips += count
        if status == "violation":
            violations.append(row)

    baseline_total = None
    baseline_category_max: dict[str, int] = {}
    baseline_classification_max: dict[str, int] = {}
    baseline_unowned_max = 0
    if args.baseline.exists():
        baseline_data = json.loads(args.baseline.read_text(encoding="utf-8"))
        baseline_total = int(baseline_data.get("max_total_skips", 0))
        baseline_category_max = {k: int(v) for k, v in baseline_data.get("max_category_skips", {}).items()}
        baseline_classification_max = {
            k: int(v) for k, v in baseline_data.get("max_classification_skips", {}).items()
        }
        baseline_unowned_max = int(baseline_data.get("max_unowned_skips", 0))

    total_skips = len(reasons)
    regression = baseline_total is not None and total_skips > baseline_total
    category_regressions = {
        k: {"actual": v, "max": baseline_category_max[k]}
        for k, v in category_counts.items()
        if k in baseline_category_max and v > baseline_category_max[k]
    }
    classification_regressions = {
        k: {"actual": v, "max": baseline_classification_max[k]}
        for k, v in classification_counts.items()
        if k in baseline_classification_max and v > baseline_classification_max[k]
    }
    unowned_regression = unowned_skips > baseline_unowned_max

    report = {
        "total_skips": total_skips,
        "baseline_max_total_skips": baseline_total,
        "regression": regression,
        "category_counts": category_counts,
        "classification_counts": classification_counts,
        "unowned_skips": unowned_skips,
        "baseline_max_unowned_skips": baseline_unowned_max,
        "baseline_max_category_skips": baseline_category_max,
        "category_regressions": category_regressions,
        "baseline_max_classification_skips": baseline_classification_max,
        "classification_regressions": classification_regressions,
        "unowned_regression": unowned_regression,
        "classified": classified,
        "violations": violations,
    }
    if args.write_report:
        args.write_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"total skipped entries: {total_skips}")
    print(f"category counts: {json.dumps(category_counts, sort_keys=True)}")
    print(f"classification counts: {json.dumps(classification_counts, sort_keys=True)}")
    print(f"unowned skipped entries: {unowned_skips}")
    for row in classified:
        print(
            f"- [{row['status']}]/{row['category']}/{row['classification']} "
            f"x{row['count']} :: {row['reason']} ({row['detail']})"
        )

    if regression:
        print(
            f"ERROR: skip count regression detected (total {total_skips} > baseline {baseline_total}).",
            file=sys.stderr,
        )
    if category_regressions:
        print("ERROR: skip category regression(s) detected:", file=sys.stderr)
        for category, data in sorted(category_regressions.items()):
            print(f"  - {category}: {data['actual']} > {data['max']}", file=sys.stderr)
    if classification_regressions:
        print("ERROR: skip classification regression(s) detected:", file=sys.stderr)
        for classification, data in sorted(classification_regressions.items()):
            print(f"  - {classification}: {data['actual']} > {data['max']}", file=sys.stderr)
    if unowned_regression:
        print(
            f"ERROR: unowned skip regression detected ({unowned_skips} > {baseline_unowned_max}).",
            file=sys.stderr,
        )
    if violations:
        print("ERROR: policy-violating skip reasons detected:", file=sys.stderr)
        for v in violations:
            print(f"  - x{v['count']} {v['reason']} ({v['detail']})", file=sys.stderr)

    return 1 if (
        regression
        or category_regressions
        or classification_regressions
        or unowned_regression
        or violations
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
