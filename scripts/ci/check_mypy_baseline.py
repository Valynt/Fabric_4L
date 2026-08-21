#!/usr/bin/env python3
"""Run mypy and enforce a per-file error baseline.

Fails if any file has more mypy errors than its baseline. Reductions are allowed.
This isolates legacy typing debt (e.g. app_monolith.py) while preventing new code
from adding to the debt.

Usage:
    python scripts/ci/check_mypy_baseline.py \
        --service-dir services/layer1-ingestion \
        --baseline config/ci/mypy_baseline_layer1.json \
        --paths src

    python scripts/ci/check_mypy_baseline.py ... --write-baseline
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ERROR_RE = re.compile(r"^(.*?):\d+: error: .*$", re.MULTILINE)


class MypyInvocationError(RuntimeError):
    """Raised when mypy exits before emitting usable diagnostics.

    This covers tooling failures (mypy not installed, invalid arguments,
    config load errors) that would otherwise be silently swallowed,
    causing the ratchet to fail open with an empty (0-error) count.
    """


def _run_mypy(service_dir: Path, paths: list[str], extra_args: list[str]) -> str:
    # Use ``sys.executable -m mypy`` so the check works on Windows where the
    # ``mypy`` console-script entrypoint is not guaranteed to be on PATH.
    cmd = [sys.executable, "-m", "mypy", *paths, *extra_args]
    result = subprocess.run(
        cmd,
        cwd=service_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    # Fail closed on tooling failures: if mypy exited non-zero but produced
    # no parseable ``file:line: error:`` diagnostics, the invocation itself
    # failed (missing mypy, bad args, config error). Returning an empty
    # count would let the ratchet report "Mypy baseline OK" and hide the
    # failure, so surface it as an explicit error instead.
    output = result.stdout + result.stderr
    if result.returncode != 0 and not ERROR_RE.search(output):
        raise MypyInvocationError(
            f"mypy exited with code {result.returncode} but produced no "
            f"parseable diagnostics. This indicates a tooling failure "
            f"(mypy not installed, invalid arguments, or config load "
            f"error). Output:\n{output}"
        )
    return output


def _count_errors(output: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for match in ERROR_RE.finditer(output):
        file_path = match.group(1).strip().replace("\\", "/")
        if file_path.startswith("Found ") or file_path.endswith(" files"):
            continue
        counts[file_path] = counts.get(file_path, 0) + 1
    return counts


def _load_baseline(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {str(k): int(v) for k, v in data.items()}


def _check(counts: dict[str, int], baseline: dict[str, int]) -> tuple[bool, list[str]]:
    ok = True
    messages: list[str] = []
    for file_path, count in sorted(counts.items()):
        allowed = baseline.get(file_path, 0)
        if count > allowed:
            ok = False
            messages.append(
                f"{file_path}: {count} errors (baseline {allowed}); +{count - allowed}"
            )
    return ok, messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-dir", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--paths", nargs="+", default=["src"])
    parser.add_argument("--mypy-args", default="")
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)

    try:
        output = _run_mypy(
            args.service_dir.resolve(),
            args.paths,
            args.mypy_args.split() if args.mypy_args else [],
        )
    except MypyInvocationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    counts = _count_errors(output)

    if args.write_baseline:
        baseline_data = dict(sorted(counts.items()))
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(
            json.dumps(baseline_data, indent=2, sort_keys=True) + "\n"
        )
        total = sum(counts.values())
        print(
            f"Wrote baseline: {total} errors across {len(counts)} files to {args.baseline}"
        )
        return 0

    baseline = _load_baseline(args.baseline)
    ok, messages = _check(counts, baseline)
    total = sum(counts.values())
    baseline_total = sum(baseline.values())

    if not ok:
        print("Mypy baseline exceeded in the following files:", file=sys.stderr)
        for msg in messages:
            print(f"  - {msg}", file=sys.stderr)
        print(
            f"Total errors: {total}; baseline total: {baseline_total}",
            file=sys.stderr,
        )
        return 1

    print(f"Mypy baseline OK: {total} errors (baseline {baseline_total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
