#!/usr/bin/env python3
"""Validate build/promotion workflow artifact contract compatibility."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_KEYS = {
    "layer",
    "image_digest",
    "published_tag",
    "source_commit_sha",
    "source_version",
    "build_timestamp",
    "environment",
}
BUILD_MARKERS = (
    "build-metadata-${{ matrix.layer }}",
    '"image_digest"',
    '"published_tag"',
    '"source_commit_sha"',
    '"source_version"',
    '"build_timestamp"',
    '"environment"',
)
PROMOTION_MARKERS = (
    "pattern: build-metadata-*",
    'json.load(open(sys.argv[1]))["image_digest"]',
    'json.load(open(sys.argv[1]))["published_tag"]',
)
SEMVER_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.-]+)?$")
PACKAGE_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.-]+)?$")
ISO_UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build-workflow", type=Path, required=True)
    p.add_argument("--promotion-workflow", type=Path, required=True)
    p.add_argument("--metadata-dir", type=Path)
    return p.parse_args()


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def _published_tag_valid(value: str) -> bool:
    return value.startswith("sha-") or bool(SEMVER_RE.match(value))


def main() -> int:
    args = parse_args()
    build_text = args.build_workflow.read_text(encoding="utf-8")
    promo_text = args.promotion_workflow.read_text(encoding="utf-8")

    for marker in BUILD_MARKERS:
        if marker not in build_text:
            fail(f"Missing build artifact contract marker in {args.build_workflow}: {marker}")
    for marker in PROMOTION_MARKERS:
        if marker not in promo_text:
            fail(f"Missing promotion artifact contract marker in {args.promotion_workflow}: {marker}")

    if args.metadata_dir is not None:
        files = sorted(args.metadata_dir.glob("*.json"))
        if not files:
            fail(f"No metadata JSON files found in {args.metadata_dir}")
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            missing = REQUIRED_KEYS - set(payload.keys())
            if missing:
                fail(f"{path} missing keys: {sorted(missing)}")
            if not str(payload["image_digest"]).startswith("sha256:"):
                fail(f"{path} has invalid image_digest {payload['image_digest']!r}")
            if not _published_tag_valid(str(payload["published_tag"])):
                fail(f"{path} has invalid published_tag {payload['published_tag']!r}")
            if len(str(payload["source_commit_sha"])) != 40:
                fail(f"{path} has invalid source_commit_sha length")
            if not PACKAGE_SEMVER_RE.match(str(payload["source_version"])):
                fail(f"{path} has invalid source_version {payload['source_version']!r}")
            if not ISO_UTC_RE.match(str(payload["build_timestamp"])):
                fail(f"{path} has invalid build_timestamp {payload['build_timestamp']!r}")
            if str(payload["environment"]).lower() in {"", "unknown", "placeholder"}:
                fail(f"{path} has invalid environment {payload['environment']!r}")

    print("Build/promotion artifact schema contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
