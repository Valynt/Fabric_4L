#!/usr/bin/env python3
"""Fail-closed root aggregate maturity gate checks.

The root package scripts must not pass when pnpm selects zero package scripts.
This runner keeps the expected workspace checks explicit, provides a named gate
router for CI and npm scripts, and reports optional gates as not_applicable
instead of silently succeeding.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parents[2]

GateStatus = Literal["passed", "failed", "not_applicable", "config_error"]
CheckStatus = Literal["passed", "failed"]


@dataclass(frozen=True)
class PackageCheck:
    package_path: str
    script: str


@dataclass(frozen=True)
class GateDefinition:
    name: str
    description: str
    required: bool


@dataclass(frozen=True)
class CheckResult:
    package_path: str
    script: str
    command: tuple[str, ...]
    status: CheckStatus
    exit_code: int

    def to_json(self) -> dict[str, object]:
        return {
            "package_path": self.package_path,
            "script": self.script,
            "command": list(self.command),
            "status": self.status,
            "exit_code": self.exit_code,
        }


@dataclass(frozen=True)
class GateResult:
    gate: str
    status: GateStatus
    exit_code: int
    required: bool
    checks_planned: int
    checks_passed: int
    checks_failed: int
    checks: tuple[CheckResult, ...]
    message: str

    def to_json(self) -> dict[str, object]:
        return {
            "gate": self.gate,
            "status": self.status,
            "exit_code": self.exit_code,
            "required": self.required,
            "checks_planned": self.checks_planned,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "checks": [check.to_json() for check in self.checks],
            "message": self.message,
        }


# Required package aggregate checks that must fail closed if the package/script
# matrix drifts. These are the root npm scripts that previously depended on
# pnpm workspace selection behavior.
EXPECTED_CHECKS: dict[str, tuple[PackageCheck, ...]] = {
    "typecheck": (
        PackageCheck("apps/web", "typecheck"),
        PackageCheck("packages/config", "typecheck"),
        PackageCheck("packages/platform-contract", "typecheck"),
        PackageCheck("packages/eslint-plugin-fabric-contracts", "typecheck"),
    ),
    "lint": (
        PackageCheck("apps/web", "lint"),
        PackageCheck("packages/eslint-plugin-fabric-contracts", "lint"),
    ),
    "test": (
        PackageCheck("apps/web", "test"),
        PackageCheck("packages/config", "test"),
        PackageCheck("packages/platform-contract", "test"),
        PackageCheck("packages/eslint-plugin-fabric-contracts", "test"),
    ),
}

# Named maturity gates exposed by the root router. Gates without configured
# package checks are intentionally represented as not_applicable until a
# concrete package/script matrix is added, so CI can annotate them explicitly.
GATE_DEFINITIONS: dict[str, GateDefinition] = {
    "lint": GateDefinition("lint", "Root lint checks across canonical packages", True),
    "test": GateDefinition("test", "Root test checks across canonical packages", True),
    "security": GateDefinition("security", "Security maturity gate", False),
    "schema": GateDefinition("schema", "Schema and contract maturity gate", False),
    "isolation": GateDefinition("isolation", "Tenant isolation maturity gate", False),
    "crawler": GateDefinition("crawler", "Crawler maturity gate", False),
    "router": GateDefinition("router", "Router governance maturity gate", False),
    "db-migrate-status": GateDefinition(
        "db-migrate-status", "Database migration status maturity gate", False
    ),
    "typecheck": GateDefinition(
        "typecheck", "Root type checks across canonical packages", True
    ),
}

SUPPORTED_GATES: tuple[str, ...] = (
    "lint",
    "test",
    "security",
    "schema",
    "isolation",
    "crawler",
    "router",
    "db-migrate-status",
    "typecheck",
)

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


class AggregateCheckError(RuntimeError):
    """Raised when aggregate check configuration or execution fails."""


def _load_package_json(path: Path) -> dict[str, object]:
    package_json = path / "package.json"
    if not package_json.exists():
        raise AggregateCheckError(f"Missing expected package manifest: {package_json}")
    with package_json.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _supported_gate_names(include_all: bool = False) -> tuple[str, ...]:
    if include_all:
        return (*SUPPORTED_GATES, "all")
    return SUPPORTED_GATES


def validate_supported_gate(target: str) -> None:
    if target in _supported_gate_names(include_all=True):
        return
    valid = ", ".join(_supported_gate_names(include_all=True))
    raise AggregateCheckError(
        f"Unsupported aggregate check {target!r}; expected one of: {valid}"
    )


def validate_expected_checks(
    target: str, repo_root: Path = REPO_ROOT
) -> tuple[PackageCheck, ...]:
    validate_supported_gate(target)
    checks = EXPECTED_CHECKS.get(target, ())
    definition = GATE_DEFINITIONS.get(target)
    if definition and not definition.required and not checks:
        return checks
    if not checks:
        raise AggregateCheckError(
            f"Aggregate check {target!r} has zero package checks configured"
        )

    for check in checks:
        package_dir = repo_root / check.package_path
        package = _load_package_json(package_dir)
        scripts = package.get("scripts")
        if not isinstance(scripts, dict) or check.script not in scripts:
            package_name = package.get("name", check.package_path)
            raise AggregateCheckError(
                f"Missing required script {check.script!r} in {check.package_path}/package.json "
                f"({package_name})"
            )

    return checks


def default_runner(
    command: Sequence[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which(command[0])
    if executable is None:
        print(f"Command not found: {command[0]}", file=sys.stderr)
        return subprocess.CompletedProcess(command, 127)
    resolved_command = [executable, *command[1:]]
    return subprocess.run(resolved_command, cwd=cwd, text=True, check=False)


def run_gate(
    target: str,
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
    *,
    quiet: bool = False,
) -> GateResult:
    validate_supported_gate(target)
    if target == "all":
        raise AggregateCheckError("run_gate() cannot run the synthetic 'all' target")

    definition = GATE_DEFINITIONS[target]
    checks = validate_expected_checks(target, repo_root)
    if not checks:
        message = (
            f"Root aggregate {target}: no configured checks; gate is not_applicable."
        )
        if not quiet:
            print(message)
        return GateResult(
            gate=target,
            status="not_applicable",
            exit_code=0,
            required=definition.required,
            checks_planned=0,
            checks_passed=0,
            checks_failed=0,
            checks=(),
            message=message,
        )

    if not quiet:
        print(f"Root aggregate {target}: {len(checks)} package checks planned.")

    results: list[CheckResult] = []
    for check in checks:
        command = ("pnpm", "--dir", check.package_path, "run", check.script)
        if not quiet:
            print(f"\n## {check.package_path}:{check.script}")
        result = runner(command, repo_root)
        status: CheckStatus = "passed" if result.returncode == 0 else "failed"
        results.append(
            CheckResult(
                package_path=check.package_path,
                script=check.script,
                command=command,
                status=status,
                exit_code=result.returncode,
            )
        )

    failures = [result for result in results if result.status == "failed"]
    passed = len(results) - len(failures)
    status: GateStatus = "failed" if failures else "passed"
    exit_code = 1 if failures else 0
    message = (
        f"Root aggregate {target} summary: {passed} passed, {len(failures)} failed."
    )
    if not quiet:
        print(f"\n{message}")
        for failure in failures:
            print(
                f" - {failure.package_path}:{failure.script} failed with exit code {failure.exit_code}",
                file=sys.stderr,
            )

    return GateResult(
        gate=target,
        status=status,
        exit_code=exit_code,
        required=definition.required,
        checks_planned=len(results),
        checks_passed=passed,
        checks_failed=len(failures),
        checks=tuple(results),
        message=message,
    )


def run_all_gates(
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
    *,
    quiet: bool = False,
) -> tuple[GateResult, ...]:
    results: list[GateResult] = []
    for gate in SUPPORTED_GATES:
        if not quiet:
            print(f"\n=== {gate} ===")
        results.append(run_gate(gate, repo_root, runner, quiet=quiet))
    return tuple(results)


def run_aggregate_check(
    target: str,
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
) -> int:
    if target == "all":
        results = run_all_gates(repo_root, runner)
        if any(result.status == "failed" for result in results):
            return 1
        return 0
    return run_gate(target, repo_root, runner).exit_code


def gate_inventory() -> dict[str, object]:
    gates = [
        {
            "name": gate,
            "description": GATE_DEFINITIONS[gate].description,
            "required": GATE_DEFINITIONS[gate].required,
            "configured": gate in EXPECTED_CHECKS and bool(EXPECTED_CHECKS[gate]),
            "status": (
                "configured"
                if gate in EXPECTED_CHECKS and EXPECTED_CHECKS[gate]
                else "not_applicable"
            ),
            "checks": [
                {"package_path": check.package_path, "script": check.script}
                for check in EXPECTED_CHECKS.get(gate, ())
            ],
        }
        for gate in SUPPORTED_GATES
    ]
    gates.append(
        {
            "name": "all",
            "description": "Run every configured root aggregate maturity gate",
            "required": True,
            "configured": True,
            "status": "configured",
            "checks": [],
        }
    )
    return {"gates": gates}


def _results_payload(target: str, results: tuple[GateResult, ...]) -> dict[str, object]:
    exit_code = 1 if any(result.status == "failed" for result in results) else 0
    return {
        "target": target,
        "status": "failed" if exit_code else "passed",
        "exit_code": exit_code,
        "results": [result.to_json() for result in results],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target", nargs="?", choices=_supported_gate_names(include_all=True)
    )
    parser.add_argument(
        "--list", action="store_true", help="List supported gate names and exit."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    args = parser.parse_args(argv)

    if args.list:
        if args.json:
            print(json.dumps(gate_inventory(), indent=2, sort_keys=True))
        else:
            for gate in _supported_gate_names(include_all=True):
                print(gate)
        return 0

    if args.json and args.target is None:
        print(json.dumps(gate_inventory(), indent=2, sort_keys=True))
        return 0

    if args.target is None:
        parser.error("target is required unless --list or --json is provided")

    try:
        if args.target == "all":
            if args.json:
                with contextlib.redirect_stdout(
                    io.StringIO()
                ), contextlib.redirect_stderr(io.StringIO()):
                    results = run_all_gates(quiet=True)
            else:
                results = run_all_gates()
            payload = _results_payload(args.target, results)
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            return int(payload["exit_code"])

        if args.json:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                result = run_gate(args.target, quiet=True)
            print(
                json.dumps(
                    _results_payload(args.target, (result,)), indent=2, sort_keys=True
                )
            )
            return result.exit_code
        return run_aggregate_check(args.target)
    except AggregateCheckError as exc:
        if args.json:
            payload = {
                "target": args.target,
                "status": "config_error",
                "exit_code": 2,
                "message": str(exc),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"Root aggregate check configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
