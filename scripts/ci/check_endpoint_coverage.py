#!/usr/bin/env python3
"""Validate frontend endpoint-hook coverage against backend OpenAPI specs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
OWNED_STATUSES = {"owned", "shared"}


@dataclass(frozen=True)
class Endpoint:
    source: str
    method: str
    path: str

    @property
    def key(self) -> str:
        return f"{self.source}:{self.method} {self.path}"


def load_openapi_endpoints(openapi_dir: Path) -> dict[str, Endpoint]:
    endpoints: dict[str, Endpoint] = {}
    for spec_path in sorted(openapi_dir.glob("*.json")):
        source = spec_path.stem
        with spec_path.open(encoding="utf-8") as fh:
            spec = json.load(fh)
        for path, methods in spec.get("paths", {}).items():
            for method in methods:
                if method.lower() not in HTTP_METHODS:
                    continue
                endpoint = Endpoint(source=source, method=method.upper(), path=path)
                endpoints[endpoint.key] = endpoint
    return endpoints


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(value)


def check_registry(registry_path: Path, openapi_dir: Path) -> tuple[int, str]:
    today = dt.date.today()
    with registry_path.open(encoding="utf-8") as fh:
        registry = json.load(fh)

    policy = registry.get("policy", {})
    min_coverage = float(policy.get("minimumCoverage", 0.0))
    stale_days = int(policy.get("staleOwnedDays", 60))
    orphan_days = int(policy.get("orphanGraceDays", 14))

    endpoints = load_openapi_endpoints(openapi_dir)
    mappings = registry.get("mappings", [])

    registry_index: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    stale: list[str] = []

    for mapping in mappings:
        source = mapping.get("source")
        method = str(mapping.get("method", "")).upper()
        path = mapping.get("path")
        if not source or not method or not path:
            continue

        key = f"{source}:{method} {path}"
        if key in registry_index:
            duplicates.append(key)
            continue
        registry_index[key] = mapping

        status = str(mapping.get("status", "")).lower()
        reviewed_on = parse_date(mapping.get("lastReviewed"))
        if status in OWNED_STATUSES and reviewed_on:
            age_days = (today - reviewed_on).days
            if age_days > stale_days:
                stale.append(
                    f"- {key} (hook={mapping.get('hook')}, lastReviewed={reviewed_on}, age={age_days}d > {stale_days}d)"
                )

    missing = sorted(set(endpoints.keys()) - set(registry_index.keys()))

    orphan: list[str] = []
    for key, mapping in sorted(registry_index.items()):
        if key in endpoints:
            continue
        reviewed_on = parse_date(mapping.get("lastReviewed"))
        age_days = (today - reviewed_on).days if reviewed_on else orphan_days + 1
        if age_days > orphan_days:
            orphan.append(f"- {key} (age={age_days}d > {orphan_days}d)")

    owned_count = 0
    trackable_count = 0
    for mapping in registry_index.values():
        status = str(mapping.get("status", "")).lower()
        if status in {"orphaned", "retired"}:
            continue
        trackable_count += 1
        if status in OWNED_STATUSES:
            owned_count += 1

    coverage = (owned_count / trackable_count) if trackable_count else 1.0
    policy_breaches: list[str] = []
    if coverage < min_coverage:
        policy_breaches.append(
            f"- coverage={coverage:.2%} is below minimumCoverage={min_coverage:.2%} (owned={owned_count}, trackable={trackable_count})"
        )

    lines = [
        "Endpoint Hook Coverage Check",
        "=" * 80,
        f"OpenAPI endpoints discovered: {len(endpoints)}",
        f"Registry mappings loaded: {len(registry_index)}",
        f"Coverage: {coverage:.2%} (owned={owned_count}, trackable={trackable_count}, minimum={min_coverage:.2%})",
        "",
    ]

    if duplicates:
        lines.append("Duplicate mappings")
        lines.append("-" * 80)
        lines.extend(f"- {item}" for item in duplicates)
        lines.append("")

    lines.append("Missing mappings (in OpenAPI but absent from registry)")
    lines.append("-" * 80)
    if missing:
        lines.extend(f"- {item}" for item in missing)
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("Stale mappings (owned/shared not reviewed within staleOwnedDays)")
    lines.append("-" * 80)
    lines.extend(stale or ["(none)"])
    lines.append("")

    lines.append("Orphan mappings (registry entries not in OpenAPI past orphanGraceDays)")
    lines.append("-" * 80)
    lines.extend(orphan or ["(none)"])
    lines.append("")

    lines.append("Policy threshold breaches")
    lines.append("-" * 80)
    lines.extend(policy_breaches or ["(none)"])

    report = "\n".join(lines)
    has_failures = bool(missing or stale or orphan or policy_breaches or duplicates)
    return (1 if has_failures else 0), report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        default="frontend/contracts/endpoint-hook-registry.json",
        type=Path,
        help="Path to endpoint-hook registry JSON file.",
    )
    parser.add_argument(
        "--openapi-dir",
        default="contracts/openapi",
        type=Path,
        help="Directory containing backend OpenAPI specs (*.json).",
    )
    parser.add_argument(
        "--write-report",
        type=Path,
        default=None,
        help="Optional JSON report path for actionable debt tracking.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    code, report = check_registry(args.registry, args.openapi_dir)
    print(report)
    if args.write_report:
        today = dt.date.today().isoformat()
        report_payload = {
            "generated_on": today,
            "status": "fail" if code else "pass",
            "registry": args.registry.as_posix(),
            "openapi_dir": args.openapi_dir.as_posix(),
            "summary": report,
        }
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
