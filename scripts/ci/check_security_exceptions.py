#!/usr/bin/env python3
"""Security exception lifecycle gate.

Enforces two acceptance metrics from the Security & Tenancy hardening plan
(improvement area A — "Make the full security aggregate required"):

  1. 100% of exceptions have an owner and an expiry.
  2. Expired exceptions automatically fail CI.

It reads the reviewed-debt registry at ``config/ci/security_exceptions.yaml``
and fails closed when:

  - an entry has no ``owner`` or no ``expires_on``;
  - ``expires_on`` is not an ISO ``YYYY-MM-DD`` date;
  - ``expires_on`` is strictly before the reference date (default: today).

Baselines that are not time-boxed (no expiry) are NOT permitted for security
exceptions: every accepted finding must be remediated on a deadline.  This
script is intentionally deterministic, offline, and dependency-free so it can
run in CI as an unconditional merge gate (mirroring the
``mandatory-security-regression`` governed-control idiom).

Reference date is overridable for tests via ``--today`` (ISO date) or the
``SECURITY_EXCEPTIONS_TODAY`` environment variable.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "config" / "ci" / "security_exceptions.yaml"

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ReferenceDate(date):
    """A date type whose default reflects an injected reference date."""

    @classmethod
    def reference(cls) -> date:
        raw = os.environ.get("SECURITY_EXCEPTIONS_TODAY")
        if raw:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        return cls.today()


def iter_exceptions(
    registry_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    """Yield (key, entry) pairs from the registry's ``exceptions`` mapping."""
    raw = registry_data.get("exceptions") or {}
    if not isinstance(raw, dict):
        raise ValueError("'exceptions' must be a mapping of id -> entry")
    for key in sorted(raw):
        entry = raw[key]
        if not isinstance(entry, dict):
            raise ValueError(f"exception '{key}' must be a mapping")
        yield key, entry


def validate_registry(
    registry_data: dict[str, Any], reference: date
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings).

    Errors fail the gate closed. Warnings are informational (e.g. an
    exception expiring soon) and are not enforced, but are surfaced for
    forward visibility.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(registry_data, dict):
        return ["registry root must be a mapping"], []

    schema_version = registry_data.get("schema_version")
    if schema_version != 1:
        errors.append(f"unsupported schema_version: {schema_version!r}; expected 1")

    for key, entry in iter_exceptions(registry_data):
        prefix = f"exception '{key}'"

        owner = entry.get("owner")
        expiry = entry.get("expires_on")
        justification = entry.get("justification")
        compensating = entry.get("compensating_control")

        # Metric: 100% of exceptions have an owner.
        if not owner or not isinstance(owner, str) or not owner.strip():
            errors.append(f"{prefix}: missing required 'owner'")

        # Metric: 100% of exceptions have an expiry.
        if not expiry or not isinstance(expiry, str):
            errors.append(f"{prefix}: missing required 'expires_on'")
        elif not _parse_date(expiry):
            errors.append(f"{prefix}: 'expires_on' must be an ISO YYYY-MM-DD date")
        else:
            expires = datetime.strptime(expiry, "%Y-%m-%d").date()
            if expires < reference:
                errors.append(
                    f"{prefix}: EXPIRED on {expiry} (reference date "
                    f"{reference.isoformat()}). Remediate or re-grant before merge."
                )
            elif expires <= reference:
                warnings.append(f"{prefix}: expires today ({expiry})")
            else:
                days_left = (expires - reference).days
                if days_left <= 14:
                    warnings.append(f"{prefix}: expiring within {days_left} days ({expiry})")

        # Reviewed-existing-debt baseline requires justification + compensating
        # control so baselines do not silently become permanent acceptance.
        if not justification or not isinstance(justification, str) or not justification.strip():
            errors.append(f"{prefix}: missing required 'justification' (baseline exceptions must be reviewed debt, not silent)")
        if not compensating or not isinstance(compensating, str) or not compensating.strip():
            errors.append(f"{prefix}: missing required 'compensating_control'")

        # Enforce ISO format for these fields (defensive; not a findable).
        for fname in ("owner", "justification", "compensating_control", "ticket"):
            val = entry.get(fname)
            if val is not None and not isinstance(val, str):
                errors.append(f"{prefix}: '{fname}' must be a string")

    return errors, warnings


def _parse_date(value: object) -> bool:
    """Parse and validate an ISO date string used across the file."""
    if not isinstance(value, str):
        return False
    if not _ISO_DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"registry not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: registry root must be a mapping")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help=f"path to the security exceptions registry (default: {DEFAULT_REGISTRY})",
    )
    parser.add_argument(
        "--reference",
        type=str,
        default=None,
        help="reference date (YYYY-MM-DD). Defaults to today (or $SECURITY_EXCEPTIONS_TODAY).",
    )
    args = parser.parse_args(argv)

    if args.reference and not _parse_date(args.reference):
        print(f"error: invalid --reference date: {args.reference}", file=sys.stderr)
        return 2

    if args.reference:
        today = datetime.strptime(args.reference, "%Y-%m-%d").date()
    else:
        today = ReferenceDate.reference()

    try:
        registry_data = load_registry(args.registry)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    errors, warnings = validate_registry(registry_data, today)

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}", file=sys.stderr)

    if errors:
        print(
            f"\nFAILED: {len(errors)} security-exception governance error(s). "
            "Fix or re-grant the affected exceptions.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: security exception registry is compliant (reference date {today.isoformat()}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())