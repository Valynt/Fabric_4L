#!/usr/bin/env python3
"""Validate or canonicalize gate evidence_producer artifact_path entries.

Use --check in CI to fail on non-canonical paths without mutating the registry.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / ".fabric" / "gate-engineering" / "gate-registry.json"


def _canonical_path(gate_id: str) -> str:
    return f"artifacts/release/gate-{gate_id.replace('.', '-')}.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if any artifact_path is not canonical; do not rewrite the registry.",
    )
    args = parser.parse_args()

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    violations: list[str] = []
    for gate in registry.get("gates", []):
        producer = gate.get("evidence_producer")
        if not producer:
            continue
        expected = _canonical_path(gate["gate_id"])
        actual = producer.get("artifact_path", "")
        if actual != expected:
            violations.append(f"{gate['gate_id']}: expected {expected}, got {actual}")

    if args.check:
        if violations:
            print("Non-canonical artifact paths found:")
            for v in violations:
                print(f"  - {v}")
            return 1
        print("All artifact paths are canonical.")
        return 0

    for gate in registry.get("gates", []):
        producer = gate.get("evidence_producer")
        if producer:
            producer["artifact_path"] = _canonical_path(gate["gate_id"])
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print("Canonicalized artifact paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
