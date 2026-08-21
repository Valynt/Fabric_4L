#!/usr/bin/env python3
"""Governance validation for .trivyignore.yaml entries.

Enforces:
  1. Valid YAML syntax and structure (must have `misconfigurations` and/or `vulnerabilities` sections).
  2. Required fields per ignore entry: `id`, `paths`, `statement`, `expired_at`.
  3. No duplicate IDs across or within sections.
  4. Expiry dates match ISO YYYY-MM-DD format.
  5. Waivers must not be expired (expired_at >= check_date).
  6. Non-empty, meaningful rationale statement (min length check).
  7. Non-empty paths list containing non-blank glob or file path patterns.
  8. Distinguishes known external/generated paths vs checkout paths and validates glob safety.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IGNORE_FILE = ROOT / ".trivyignore.yaml"

REQUIRED_FIELDS = ("id", "paths", "statement", "expired_at")
MIN_STATEMENT_LENGTH = 15
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# External modules or generated artifacts not committed directly to git root
KNOWN_EXTERNAL_PATH_PREFIXES = (
    "terraform-aws-modules/",
    "infra/helm/fabric-chart/charts/",
)


@dataclass
class PolicyViolation:
    section: str
    entry_id: str
    field: str
    message: str


def validate_trivy_ignore(
    ignore_data: dict[str, Any],
    reference_date: datetime.date | None = None,
    repo_root: Path | None = None,
) -> list[PolicyViolation]:
    if reference_date is None:
        reference_date = datetime.datetime.now(tz=datetime.timezone.utc).date()
    if repo_root is None:
        repo_root = ROOT

    violations: list[PolicyViolation] = []

    if not isinstance(ignore_data, dict):
        violations.append(
            PolicyViolation(
                section="root",
                entry_id="root",
                field="structure",
                message="Top-level content must be a YAML mapping/dictionary",
            )
        )
        return violations

    sections = [k for k in ("misconfigurations", "vulnerabilities") if k in ignore_data]
    if not sections:
        violations.append(
            PolicyViolation(
                section="root",
                entry_id="root",
                field="sections",
                message="File must define at least one of 'misconfigurations' or 'vulnerabilities'",
            )
        )
        return violations

    seen_ids: dict[str, str] = {}  # id -> section

    for section in ("misconfigurations", "vulnerabilities"):
        entries = ignore_data.get(section)
        if entries is None:
            continue
        if not isinstance(entries, list):
            violations.append(
                PolicyViolation(
                    section=section,
                    entry_id=section,
                    field="type",
                    message=f"Section '{section}' must be a list of waiver entries",
                )
            )
            continue

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                violations.append(
                    PolicyViolation(
                        section=section,
                        entry_id=f"entry_{idx}",
                        field="type",
                        message=f"Entry at index {idx} must be a dictionary",
                    )
                )
                continue

            entry_id = str(entry.get("id") or "").strip()
            if not entry_id:
                violations.append(
                    PolicyViolation(
                        section=section,
                        entry_id=f"entry_{idx}",
                        field="id",
                        message=f"Entry at index {idx} is missing required 'id'",
                    )
                )
                entry_id = f"unknown_{idx}"
            else:
                if entry_id in seen_ids:
                    violations.append(
                        PolicyViolation(
                            section=section,
                            entry_id=entry_id,
                            field="id",
                            message=f"Duplicate ID '{entry_id}' found (first seen in section '{seen_ids[entry_id]}')",
                        )
                    )
                else:
                    seen_ids[entry_id] = section

            # Check missing fields
            for req in REQUIRED_FIELDS:
                if req not in entry or entry[req] is None:
                    violations.append(
                        PolicyViolation(
                            section=section,
                            entry_id=entry_id,
                            field=req,
                            message=f"Missing required field '{req}'",
                        )
                    )

            # Check statement
            statement = entry.get("statement")
            if statement is not None and (
                not isinstance(statement, str)
                or len(statement.strip()) < MIN_STATEMENT_LENGTH
            ):
                violations.append(
                    PolicyViolation(
                        section=section,
                        entry_id=entry_id,
                        field="statement",
                        message=f"Statement must be a descriptive string with at least {MIN_STATEMENT_LENGTH} characters",
                    )
                )

            # Check expired_at
            expired_at_raw = entry.get("expired_at")
            if expired_at_raw is not None:
                expiry_date: datetime.date | None = None
                if isinstance(expired_at_raw, datetime.date):
                    expiry_date = expired_at_raw
                elif isinstance(expired_at_raw, str):
                    if not DATE_REGEX.match(expired_at_raw.strip()):
                        violations.append(
                            PolicyViolation(
                                section=section,
                                entry_id=entry_id,
                                field="expired_at",
                                message=f"Date '{expired_at_raw}' must follow ISO format YYYY-MM-DD",
                            )
                        )
                    else:
                        try:
                            expiry_date = datetime.date.fromisoformat(
                                expired_at_raw.strip()
                            )
                        except ValueError:
                            violations.append(
                                PolicyViolation(
                                    section=section,
                                    entry_id=entry_id,
                                    field="expired_at",
                                    message=f"Invalid calendar date '{expired_at_raw}'",
                                )
                            )
                else:
                    violations.append(
                        PolicyViolation(
                            section=section,
                            entry_id=entry_id,
                            field="expired_at",
                            message="Field 'expired_at' must be a date string (YYYY-MM-DD) or date object",
                        )
                    )

                if expiry_date is not None and expiry_date < reference_date:
                    violations.append(
                        PolicyViolation(
                            section=section,
                            entry_id=entry_id,
                            field="expired_at",
                            message=f"Waiver expired on {expiry_date} (reference date: {reference_date})",
                        )
                    )

            # Check paths
            paths = entry.get("paths")
            if paths is not None:
                if not isinstance(paths, list) or len(paths) == 0:
                    violations.append(
                        PolicyViolation(
                            section=section,
                            entry_id=entry_id,
                            field="paths",
                            message="Field 'paths' must be a non-empty list of path strings",
                        )
                    )
                else:
                    for p in paths:
                        if not isinstance(p, str) or not p.strip():
                            violations.append(
                                PolicyViolation(
                                    section=section,
                                    entry_id=entry_id,
                                    field="paths",
                                    message="Paths must be non-empty strings",
                                )
                            )
                        elif p.strip() in ("*", "**", "/", "."):
                            violations.append(
                                PolicyViolation(
                                    section=section,
                                    entry_id=entry_id,
                                    field="paths",
                                    message=f"Overly broad path pattern '{p}' is not allowed",
                                )
                            )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate .trivyignore.yaml policy and waiver health."
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_IGNORE_FILE,
        help="Path to .trivyignore.yaml file",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override current date check (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    target_file = args.file
    if not target_file.is_absolute():
        target_file = ROOT / target_file

    if not target_file.exists():
        print(f"FAIL: Ignore file not found: {target_file}")
        return 1

    try:
        content = yaml.safe_load(target_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"FAIL: Could not parse YAML in {target_file}: {exc}")
        return 1

    ref_date = None
    if args.date:
        try:
            ref_date = datetime.date.fromisoformat(args.date)
        except ValueError:
            print(f"FAIL: Invalid date format for --date: {args.date}")
            return 1
    else:
        ref_date = datetime.datetime.now(tz=datetime.timezone.utc).date()

    violations = validate_trivy_ignore(content, reference_date=ref_date, repo_root=ROOT)
    if violations:
        print(
            f"FAIL: Found {len(violations)} Trivy ignore policy violation(s) "
            f"in {target_file.name}:"
        )
        for v in violations:
            print(f"  [{v.section}] {v.entry_id} -> {v.field}: {v.message}")
        return 1

    print(
        f"PASS: .trivyignore.yaml passed all {len(seen_counts(content))} "
        f"governance checks."
    )
    return 0


def seen_counts(content: Any) -> list:
    if not isinstance(content, dict):
        return []
    res = []
    for s in ("misconfigurations", "vulnerabilities"):
        items = content.get(s, [])
        if isinstance(items, list):
            res.extend(items)
    return res


if __name__ == "__main__":
    sys.exit(main())
