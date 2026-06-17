#!/usr/bin/env python3
"""Unified compatibility shim gate runner.

This runner reads subcommand inventory from
`docs/governance/compatibility-debt-registry.md` and dispatches existing checks
as subprocess commands. It does not replace leaf checks; it orchestrates them.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ci.compatibility_registry import REGISTRY_PATH, GateCheckEntry, parse_gate_inventory


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    subcommand: str
    command: str
    required: bool
    exit_code: int
    duration_seconds: float


def _load_inventory() -> list[GateCheckEntry]:
    inventory = parse_gate_inventory(REGISTRY_PATH)
    if not inventory:
        raise RuntimeError(
            "No compatibility gate inventory entries found. "
            "Ensure COMPAT_GATE_INVENTORY markers exist in the registry document."
        )
    return inventory


def _inventory_map(inventory: list[GateCheckEntry]) -> dict[str, GateCheckEntry]:
    return {entry.subcommand: entry for entry in inventory}


def _run_entry(entry: GateCheckEntry) -> CheckResult:
    start = time.perf_counter()
    proc = subprocess.run(
        entry.command,
        shell=True,
        cwd=str(ROOT),
        check=False,
    )
    elapsed = round(time.perf_counter() - start, 3)
    return CheckResult(
        check_id=entry.check_id,
        subcommand=entry.subcommand,
        command=entry.command,
        required=entry.required,
        exit_code=proc.returncode,
        duration_seconds=elapsed,
    )


def _print_list(inventory: list[GateCheckEntry]) -> int:
    print("Compatibility shim gate inventory:")
    for entry in inventory:
        req = "required" if entry.required else "optional"
        print(f"- {entry.subcommand} ({entry.check_id}, {req}, scope={entry.scope})")
        print(f"  owner: {entry.owner}")
        print(f"  command: {entry.command}")
    return 0


def _print_list_json(inventory: list[GateCheckEntry]) -> int:
    payload = {
        "registry": str(REGISTRY_PATH.relative_to(ROOT).as_posix()),
        "inventory": [
            {
                "check_id": entry.check_id,
                "subcommand": entry.subcommand,
                "owner": entry.owner,
                "command": entry.command,
                "required": entry.required,
                "scope": entry.scope,
                "notes": entry.notes,
            }
            for entry in inventory
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _print_results(results: list[CheckResult], json_output: bool) -> None:
    payload = {
        "registry": str(REGISTRY_PATH.relative_to(ROOT).as_posix()),
        "results": [asdict(result) for result in results],
    }
    if json_output:
        print(json.dumps(payload, indent=2))
        return

    print("Compatibility shim gate results:")
    for result in results:
        status = "PASS" if result.exit_code == 0 else "FAIL"
        req = "required" if result.required else "optional"
        print(
            f"- {status} {result.subcommand} ({result.check_id}, {req}) "
            f"exit={result.exit_code} duration={result.duration_seconds:.3f}s"
        )


def _exit_code(results: list[CheckResult], strict: bool) -> int:
    if not strict:
        return 0
    for result in results:
        if result.required and result.exit_code != 0:
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    list_parser = subparsers.add_parser("list", help="List registry-defined compatibility checks.")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    list_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero if any required check fails.",
    )

    run_parser = subparsers.add_parser("run", help="Run one registry subcommand.")
    run_parser.add_argument("subcommand", help="Registry subcommand to execute.")
    run_parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    run_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero if any required check fails.",
    )

    run_all_parser = subparsers.add_parser("run-all", help="Run all required registry checks.")
    run_all_parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    run_all_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero if any required check fails.",
    )

    args = parser.parse_args(argv)

    inventory = _load_inventory()
    inventory_by_subcommand = _inventory_map(inventory)

    if args.action == "list":
        if args.json:
            return _print_list_json(inventory)
        return _print_list(inventory)

    if args.action == "run":
        entry = inventory_by_subcommand.get(args.subcommand)
        if entry is None:
            print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
            print("Use `list` to show supported subcommands.", file=sys.stderr)
            return 2
        result = _run_entry(entry)
        _print_results([result], args.json)
        return _exit_code([result], args.strict)

    if args.action == "run-all":
        entries = [entry for entry in inventory if entry.required]
        results = [_run_entry(entry) for entry in entries]
        _print_results(results, args.json)
        return _exit_code(results, args.strict)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
