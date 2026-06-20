#!/usr/bin/env python3
"""Set all gate evidence_producer artifact_path entries to canonical paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / ".fabric" / "gate-engineering" / "gate-registry.json"


def _canonical_path(gate_id: str) -> str:
    return f"artifacts/release/gate-{gate_id.replace('.', '-')}.json"


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for gate in registry["gates"]:
        producer = gate.get("evidence_producer")
        if producer:
            producer["artifact_path"] = _canonical_path(gate["gate_id"])
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print("Canonicalized artifact paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
