#!/usr/bin/env python3
"""Run compatibility shim inventory checks from the governance registry."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "governance" / "compatibility-debt-registry.md"
START = "<!-- COMPAT_GATE_INVENTORY_START -->"
END = "<!-- COMPAT_GATE_INVENTORY_END -->"


def _load_inventory() -> list[dict[str, object]]:
    text = REGISTRY.read_text(encoding="utf-8")
    try:
        block = text.split(START, 1)[1].split(END, 1)[0]
        payload = block.split("```json", 1)[1].split("```", 1)[0]
    except IndexError as exc:
        raise SystemExit(f"Could not locate compatibility gate inventory in {REGISTRY}") from exc

    inventory = json.loads(payload)
    if not isinstance(inventory, list):
        raise SystemExit("Compatibility gate inventory must be a JSON list")
    return inventory


def _run_check(entry: dict[str, object]) -> dict[str, object]:
    check_id = str(entry.get("check_id", "unknown"))
    subcommand = str(entry.get("subcommand", "unknown"))
    command = str(entry.get("command", "")).strip()
    if not command:
        print(f"FAIL {check_id} ({subcommand}) has no command")
        return {"check_id": check_id, "subcommand": subcommand, "status": "fail", "exit_code": 1, "command": command}

    print(f"-> {check_id} {subcommand}: {command}")

    sub_commands = [c.strip() for c in command.split("&&")]
    for sub_cmd in sub_commands:
        if not sub_cmd:
            continue
        parsed_cmd = shlex.split(sub_cmd)
        completed = subprocess.run(parsed_cmd, cwd=ROOT, shell=False)
        if completed.returncode != 0:
            print(f"FAIL {check_id} ({subcommand}) exited {completed.returncode} on command: {sub_cmd}")
            return {"check_id": check_id, "subcommand": subcommand, "status": "fail", "exit_code": completed.returncode, "command": command}

    print(f"PASS {check_id} ({subcommand})")
    return {"check_id": check_id, "subcommand": subcommand, "status": "pass", "exit_code": 0, "command": command}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_all = subparsers.add_parser("run-all", help="Run every required inventory check")
    run_all.add_argument("--strict", action="store_true", help="Fail when any required check fails")
    run_all.add_argument("--include-optional", action="store_true", help="Run optional checks too")
    run_all.add_argument("--json", action="store_true", help="Emit a JSON summary to stdout after the human-readable log")

    args = parser.parse_args(argv)
    inventory = _load_inventory()

    results: list[dict[str, object]] = []
    failures = 0
    for entry in inventory:
        required = bool(entry.get("required", False))
        if not required and not args.include_optional:
            continue
        result = _run_check(entry)
        results.append(result)
        failures += 1 if result["status"] != "pass" else 0

    if args.json:
        summary = {
            "status": "fail" if failures else "pass",
            "failures": failures,
            "checks": results,
        }
        print(json.dumps(summary, indent=2))

    if failures:
        print(f"Compatibility shim gate failed: {failures} check(s) failed")
        return 1 if args.strict else 0

    print("Compatibility shim gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
