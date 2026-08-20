"""Argument-only compatibility adapter for the canonical test-debt evaluator."""
from __future__ import annotations

import argparse
from pathlib import Path

from check_test_skip_governance import main as canonical_main


def delegate(argv: list[str] | None = None, *, collection_mode: bool = False) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    if collection_mode:
        parser.add_argument("collection", nargs="?", type=Path)
    parser.add_argument("--register", default="config/ci/test_skip_register.yaml")
    parser.add_argument("--json-out", "--write-report", dest="json_out")
    parser.add_argument("--md-out")
    parser.add_argument("--baseline")
    parser.add_argument("--allowlist")
    parser.add_argument("--exclude", action="append")
    parser.add_argument("--warn-only", action="store_true")
    args, _ = parser.parse_known_args(argv)
    canonical = ["--register", args.register]
    if args.json_out:
        canonical += ["--json-out", args.json_out]
    if args.md_out:
        canonical += ["--md-out", args.md_out]
    if collection_mode and args.collection:
        canonical += ["--collection-evidence", str(args.collection)]
    return canonical_main(canonical)
