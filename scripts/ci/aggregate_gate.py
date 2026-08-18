#!/usr/bin/env python3
"""Aggregate gate arbiter for the V1-CI-001 staged check consolidation.

An aggregate check (``01-repository-integrity`` .. ``08-release-evidence``)
performs no substantive testing; it only summarizes the results of the
existing jobs it fans in from. This script is the shared arbiter every
aggregate job calls.

Input is the invoking job's ``needs`` context as JSON. A child job result of
``success`` passes. A result of ``failure`` or ``cancelled`` fails the
aggregate (a failing child must fail its aggregate). A result of ``skipped``
is only acceptable when the skip was explicitly confirmed safe via a
``--skip-safe JOB=ENV_VAR`` policy entry: the named environment variable
(typically a composed change-scope expression passed in via ``env:``) must be
exactly the string ``true``. Jobs without a policy entry must succeed — any
skip or failure of those jobs fails the aggregate closed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail unless every fanned-in child job succeeded or was confirmed safe to skip."
    )
    parser.add_argument(
        "--needs-json",
        required=True,
        help="JSON serialization of the calling job's `needs` context.",
    )
    parser.add_argument(
        "--skip-safe",
        action="append",
        default=[],
        metavar="JOB=ENV_VAR",
        help=(
            "A 'skipped' result for JOB is safe only when environment variable "
            "ENV_VAR is exactly 'true'. Repeatable. Jobs without an entry must succeed."
        ),
    )
    args = parser.parse_args(argv)

    try:
        needs = json.loads(args.needs_json)
    except json.JSONDecodeError as exc:
        print(f"aggregate gate: --needs-json is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(needs, dict) or not needs:
        print("aggregate gate: --needs-json must decode to a non-empty mapping", file=sys.stderr)
        return 1

    skip_policy: dict[str, str] = {}
    for entry in args.skip_safe:
        job, sep, env_var = entry.partition("=")
        if not sep or not job or not env_var:
            print(
                f"aggregate gate: malformed --skip-safe entry {entry!r} (expected JOB=ENV_VAR)",
                file=sys.stderr,
            )
            return 1
        skip_policy[job] = env_var

    failed: list[tuple[str, str]] = []
    for job in sorted(needs):
        payload = needs[job]
        result = payload.get("result", "unknown") if isinstance(payload, dict) else "unknown"
        if result == "success":
            print(f"PASS {job}: success")
        elif result == "skipped":
            env_var = skip_policy.get(job)
            if env_var is not None and os.environ.get(env_var) == "true":
                print(f"SKIP {job}: skipped — confirmed safe ({env_var}=true)")
            else:
                failed.append((job, result))
                print(f"FAIL {job}: skipped without an explicit safe-skip confirmation")
        else:
            failed.append((job, result))
            print(f"FAIL {job}: {result}")

    total = len(needs)
    if failed:
        print(
            f"aggregate gate FAILED: {len(failed)}/{total} child job(s) failed, "
            "cancelled, or skipped without confirmation: "
            + ", ".join(f"{job}={result}" for job, result in failed),
            file=sys.stderr,
        )
        return 1
    print(f"aggregate gate PASSED: all {total} child job(s) succeeded or were confirmed safe to skip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
