"""Compare deterministic Phase B tasks through Make and the Fabric facade."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "artifacts/task-runner/shadow-parity.json"
TASKS = ("check-conflict-markers", "check-no-nul-bytes")
Runner = Callable[..., subprocess.CompletedProcess[str]]


def _run(
    command: Sequence[str],
    *,
    runner: Runner,
    env: dict[str, str],
) -> dict[str, object]:
    try:
        completed = runner(
            list(command),
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        return {
            "command": list(command),
            "exit_code": None,
            "error": str(error),
        }

    return {
        "command": list(command),
        "exit_code": completed.returncode,
    }


def build_report(
    *,
    runner: Runner = subprocess.run,
    base_env: dict[str, str] | None = None,
) -> dict[str, object]:
    env = dict(os.environ if base_env is None else base_env)
    env.update(
        {
            "FABRIC_LEGACY_MODE": "error",
            "NX_DAEMON": "false",
            "NX_NO_CLOUD": "true",
        }
    )

    results: list[dict[str, object]] = []
    for task in TASKS:
        make_result = _run(("make", task), runner=runner, env=env)
        graph_result = _run(
            ("corepack", "pnpm", "run", "fabric", "--", task),
            runner=runner,
            env=env,
        )
        passed = (
            make_result["exit_code"] == 0
            and graph_result["exit_code"] == make_result["exit_code"]
        )
        results.append(
            {
                "task": task,
                "make": make_result,
                "graph": graph_result,
                "artifacts": [],
                "passed": passed,
            }
        )

    return {
        "schema_version": 1,
        "mode": "linux-shadow",
        "cache_enabled": False,
        "passed": all(result["passed"] for result in results),
        "tasks": results,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = build_report()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{json.dumps(report, indent=2, sort_keys=True)}\n", encoding="utf-8")
    try:
        display_path = output.relative_to(ROOT)
    except ValueError:
        display_path = output

    if not report["passed"]:
        print(f"Task-runner shadow parity failed; see {display_path}", file=sys.stderr)
        return 1

    print(f"Task-runner shadow parity passed; evidence: {display_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
