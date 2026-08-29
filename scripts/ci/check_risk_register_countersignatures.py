#!/usr/bin/env python3
"""Fail on un-countersigned ACCEPTED P0 risks in the production-readiness risk register.

Fail-on-net-new philosophy: a JSON baseline lists risk IDs whose P0
countersignature gap is temporarily grandfathered (Sprint 1 / Phase 0 exit
criteria: obtain countersignatures or documented P0->P1 waivers). Any
*new* un-countersigned ACCEPTED P0 risk fails the check. P1 gaps warn only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

DEFAULT_REGISTER = "production-readiness/risk_register.yaml"


def load_baseline(path: Path | None) -> dict[str, str]:
    """Return {risk_id: reason} for grandfathered P0 countersignature gaps."""
    if path is None:
        return {}
    if not path.is_file():
        print(f"ERROR: baseline file not found: {path}", file=sys.stderr)
        sys.exit(2)
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("grandfathered", [])
    baseline: dict[str, str] = {}
    for entry in entries:
        risk_id = entry.get("id")
        if not risk_id:
            print(f"ERROR: baseline entry missing 'id': {entry}", file=sys.stderr)
            sys.exit(2)
        baseline[str(risk_id)] = str(entry.get("reason", ""))
    return baseline


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--register",
        default=DEFAULT_REGISTER,
        help=f"Path to the risk register YAML (default: {DEFAULT_REGISTER})",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="JSON file listing risk IDs whose P0 countersignature gap is grandfathered",
    )
    args = parser.parse_args()

    register_path = Path(args.register)
    if not register_path.is_file():
        print(f"ERROR: risk register not found: {register_path}", file=sys.stderr)
        return 2
    register = yaml.safe_load(register_path.read_text(encoding="utf-8"))
    risks = register.get("risks", []) if isinstance(register, dict) else []

    baseline = load_baseline(Path(args.baseline) if args.baseline else None)

    failures: list[str] = []
    grandfathered_hits: list[str] = []
    warnings: list[str] = []

    for risk in risks:
        if not isinstance(risk, dict):
            continue
        if risk.get("status") != "ACCEPTED":
            continue
        risk_id = str(risk.get("id", "<unknown>"))
        severity = str(risk.get("severity", ""))
        countersignature = risk.get("countersignature")
        signed = countersignature is not None and countersignature != "MISSING"
        if signed:
            continue
        if severity == "P0":
            if risk_id in baseline:
                grandfathered_hits.append(
                    f"  {risk_id}: grandfathered — {baseline[risk_id]}"
                )
            else:
                failures.append(
                    f"  {risk_id} (P0, ACCEPTED): countersignature is "
                    f"{'MISSING' if countersignature == 'MISSING' else 'absent'}"
                )
        elif severity == "P1":
            warnings.append(f"  {risk_id} (P1, ACCEPTED): countersignature missing (warning only)")

    if grandfathered_hits:
        print("Grandfathered P0 countersignature gaps (baseline):")
        print("\n".join(grandfathered_hits))
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    if failures:
        print("ERROR: un-countersigned ACCEPTED P0 risks (net-new, not in baseline):", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        print(
            "Obtain owner countersignatures or documented P0->P1 waivers "
            "(evolution plan Phase 0 exit criteria).",
            file=sys.stderr,
        )
        return 1

    print("✅ Risk register countersignature check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
