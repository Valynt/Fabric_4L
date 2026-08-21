#!/usr/bin/env python3
"""Enforce the operational debt registry.

Companion to config/ci/operational_debt_registry.yaml. This validator enforces
the behavior-first invariant: operational debt is tolerated only while it is
owned, tracked, and time-boxed. Expired entries fail closed (non-zero exit),
forcing either renewal with a fresh ticket or removal of the underlying debt.

Categories tracked here are operational/infrastructure debt surfaced by audits
and PR reviews. They are distinct from:
  - test skips/xfails  -> config/ci/behavior_readiness_waivers.yaml
  - legacy code markers -> config/ci/legacy_debt_approvals.json

Exit codes:
  0 = all entries valid and within their time box
  1 = one or more entries expired, missing required fields, or the registry is
      malformed

Ownership: Platform Governance. Troubleshooting: see
docs/runbooks/operational/governance-gates-troubleshooting.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - pyyaml is a CI dependency
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "config" / "ci" / "operational_debt_registry.yaml"

REQUIRED_FIELDS = (
    "id",
    "category",
    "severity",
    "owner",
    "ticket",
    "expires_on",
    "summary",
    "impact",
    "remediation",
    "verification",
)

VALID_CATEGORIES = {"sli-drift", "type-baseline", "tooling-gap", "security-hardening", "other"}
VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def _load_registry(path: Path) -> dict:
    if yaml is None:
        raise SystemExit(
            "ERROR: pyyaml is required to validate the operational debt registry",
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("entries", [])
    return data


def _parse_expires(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def validate(path: Path, *, today: date | None = None, write_report: Path | None = None) -> list[str]:
    registry = _load_registry(path)
    entries = registry.get("entries", [])
    errors: list[str] = []
    seen_ids: set[str] = set()
    today = today or date.today()
    expired: list[str] = []
    expiring_soon: list[str] = []

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{idx}] is not a mapping")
            continue

        for field in REQUIRED_FIELDS:
            value = entry.get(field)
            if value in (None, ""):
                errors.append(f"entries[{idx}].{field} is missing or empty")

        entry_id = entry.get("id")
        if entry_id:
            if entry_id in seen_ids:
                errors.append(f"entries[{idx}].id is not unique: {entry_id}")
            seen_ids.add(entry_id)

        category = entry.get("category")
        if category and category not in VALID_CATEGORIES:
            errors.append(
                f"entries[{idx}].category '{category}' is not one of {sorted(VALID_CATEGORIES)}",
            )

        severity = entry.get("severity")
        if severity and severity not in VALID_SEVERITIES:
            errors.append(
                f"entries[{idx}].severity '{severity}' is not one of {sorted(VALID_SEVERITIES)}",
            )

        expires = _parse_expires(entry.get("expires_on"))
        if entry.get("expires_on") and expires is None:
            errors.append(
                f"entries[{idx}].expires_on '{entry.get('expires_on')}' is not a valid YYYY-MM-DD date",
            )
        elif expires:
            if expires < today:
                expired.append(f"{entry_id} (expired {expires.isoformat()})")
            elif (expires - today).days <= 14:
                expiring_soon.append(f"{entry_id} (expires {expires.isoformat()})")

    if write_report is not None:
        write_report.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "total_entries": len(entries),
            "expired": expired,
            "expiring_soon": expiring_soon,
            "errors": errors,
            "entries": entries,
        }
        write_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if expired:
        errors.append(
            "Expired operational debt entries (renew with a fresh ticket or remove the debt): "
            + "; ".join(expired),
        )

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the operational debt registry.")
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--write-report", type=Path)
    args = ap.parse_args()

    errors = validate(args.registry, write_report=args.write_report)

    if errors:
        print("ERROR: operational debt registry is invalid or has expired entries:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("Operational debt registry is valid and within its time box.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
