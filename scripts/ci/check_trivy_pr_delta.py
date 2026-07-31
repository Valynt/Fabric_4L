#!/usr/bin/env python3
"""Fail when a proposed merge adds Trivy findings relative to its live target."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _results(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"Cannot read valid SARIF from {path}: {type(exc).__name__}"
        ) from None
    runs = document.get("runs")
    if not isinstance(runs, list):
        raise SystemExit(f"Invalid SARIF in {path}: runs must be a list")
    return [
        result
        for run in runs
        if isinstance(run, dict)
        for result in run.get("results", [])
        if isinstance(result, dict)
    ]


def _location(result: dict[str, Any]) -> tuple[str, int]:
    locations = result.get("locations")
    physical = (locations[0] if isinstance(locations, list) and locations else {}).get(
        "physicalLocation", {}
    )
    artifact = (
        physical.get("artifactLocation", {}) if isinstance(physical, dict) else {}
    )
    region = physical.get("region", {}) if isinstance(physical, dict) else {}
    uri = (
        artifact.get("uri", "<unknown>") if isinstance(artifact, dict) else "<unknown>"
    )
    line = region.get("startLine", 0) if isinstance(region, dict) else 0
    return str(uri), line if isinstance(line, int) else 0


def _identity(result: dict[str, Any]) -> tuple[str, str, str, int, str]:
    uri, line = _location(result)
    message = result.get("message", {})
    text = message.get("text", "") if isinstance(message, dict) else ""
    digest = hashlib.sha256(str(text).encode()).hexdigest()
    return (
        str(result.get("ruleId", "<unknown>")),
        str(result.get("level", "<unknown>")),
        uri,
        line,
        digest,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    args = parser.parse_args()

    base_results = _results(args.base)
    head_results = _results(args.head)
    base = Counter(_identity(result) for result in base_results)
    head = Counter(_identity(result) for result in head_results)
    added = head - base

    print(
        f"Trivy delta: {len(base_results)} base findings, "
        f"{len(head_results)} head findings, {sum(added.values())} new findings"
    )
    for (rule, level, uri, line, _digest), count in sorted(added.items()):
        suffix = f" (x{count})" if count > 1 else ""
        print(f"NEW {level} {rule} {uri}:{line}{suffix}")
    return 1 if added else 0


if __name__ == "__main__":
    raise SystemExit(main())
