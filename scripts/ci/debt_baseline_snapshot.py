#!/usr/bin/env python3
"""Aggregate existing checked-in debt baselines into a Phase 0 snapshot.

Reads the canonical ratchet baselines/registries (no repo scan; cheap and
robust) and writes config/ci/phase0_debt_baseline.json with counts, source
paths, and the snapshot date. This is the Phase 0 ground-truth snapshot that
future fail-on-net-new ratchets are measured against.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    import sys

    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

DEFAULT_OUTPUT = "config/ci/phase0_debt_baseline.json"
COMPATIBILITY_SHIMS_REGISTRY = "docs/governance/compatibility-debt-registry.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def type_escape_summary(path: Path) -> dict:
    data = load_json(path)
    entries = data.get("occurrences", [])
    return {"path": str(path), "approved_escapes": len(entries)}


def structural_fitness_summary(path: Path) -> dict:
    data = load_json(path)
    return {
        "path": str(path),
        "high_complexity_functions": len(data.get("high_complexity_functions", [])),
        "oversized_modules": len(data.get("oversized_modules", data.get("large_modules", []))),
        "dependency_cycles": len(data.get("dependency_cycles", [])),
    }


def legacy_debt_summary(path: Path) -> dict:
    data = load_json(path)
    counts = data.get("counts", {})
    return {"path": str(path), "counts": counts, "total": sum(counts.values())}


def operational_debt_summary(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("entries", [])
    return {"path": str(path), "entries": len(entries)}


def dead_code_summary(path: Path) -> dict:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return {"path": str(path), "allowlisted_symbols": len(lines)}


def test_skip_summary(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("entries", [])
    count = len(entries) if isinstance(entries, (list, dict)) else 0
    return {"path": str(path), "registered_skips": count}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Snapshot output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    os.chdir(root)

    snapshot = {
        "schema_version": 1,
        "snapshot_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sources": {
            "type_escape": type_escape_summary(Path("config/ci/type_escape_baseline.json")),
            "structural_fitness": structural_fitness_summary(Path("config/ci/structural_fitness_baseline.json")),
            "legacy_debt": legacy_debt_summary(Path("config/ci/legacy_debt_baseline.json")),
            "operational_debt": operational_debt_summary(Path("config/ci/operational_debt_registry.yaml")),
            "dead_code": dead_code_summary(Path("config/ci/dead_code_allowlist.txt")),
            "test_skips": test_skip_summary(Path("config/ci/test_skip_register.yaml")),
            "compatibility_shims": {"registry": COMPATIBILITY_SHIMS_REGISTRY},
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"✅ Phase 0 debt baseline snapshot written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
