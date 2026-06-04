#!/usr/bin/env python3
"""Fail-closed root aggregate and maturity gate dispatcher."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal


REPO_ROOT = Path(__file__).resolve().parents[2]
BOOL_STRINGS = {"0", "1", "false", "true", "no", "yes", "off", "on"}


class GateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    NOT_RUN = "not_run"


@dataclass(frozen=True)
class PackageCheck:
    package_path: str
    script: str


@dataclass(frozen=True)
class CommandCheck:
    command: tuple[str, ...]
    label: str
    required_paths: tuple[Path, ...] = ()
    optional: bool = False
    cwd: Path = REPO_ROOT


Check = PackageCheck | CommandCheck
GateKind = Literal["package", "command"]


@dataclass(frozen=True)
class Gate:
    name: str
    description: str
    kind: GateKind
    checks: tuple[Check, ...]


@dataclass(frozen=True)
class CheckResult:
    label: str
    command: tuple[str, ...]
    status: GateStatus
    exit_code: int
    message: str | None = None
    missing_paths: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "label": self.label,
            "command": list(self.command),
            "status": self.status.value,
            "exit_code": self.exit_code,
        }
        if self.message:
            payload["message"] = self.message
        if self.missing_paths:
            payload["missing_paths"] = list(self.missing_paths)
        return payload


@dataclass(frozen=True)
class GateResult:
    name: str
    description: str
    status: GateStatus
    exit_code: int
    checks: tuple[CheckResult, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "checks": [check.to_json() for check in self.checks],
        }


GATES: dict[str, Gate] = {
    "typecheck": Gate(
        name="typecheck",
        description="Root TypeScript/package type-check aggregate.",
        kind="package",
        checks=(
            PackageCheck("apps/web", "typecheck"),
            PackageCheck("packages/config", "typecheck"),
            PackageCheck("packages/platform-contract", "typecheck"),
            PackageCheck("packages/eslint-plugin-fabric-contracts", "typecheck"),
        ),
    ),
    "lint": Gate(
        name="lint",
        description="Root frontend/package lint aggregate.",
        kind="package",
        checks=(
            PackageCheck("apps/web", "lint"),
            PackageCheck("packages/eslint-plugin-fabric-contracts", "lint"),
        ),
    ),
    "test": Gate(
        name="test",
        description="Root frontend/package test aggregate.",
        kind="package",
        checks=(
            PackageCheck("apps/web", "test"),
            PackageCheck("packages/config", "test"),
            PackageCheck("packages/platform-contract", "test"),
            PackageCheck("packages/eslint-plugin-fabric-contracts", "test"),
        ),
    ),
    "security": Gate(
        name="security",
        description="Fast security smoke gate.",
        kind="command",
        checks=(
            CommandCheck(
                (sys.executable, "-m", "pytest", "-v", "--tb=short", "-x", "tests/security/test_security_smoke.py"),
                "security smoke pytest",
                required_paths=(Path("tests/security/test_security_smoke.py"),),
                optional=True,
            ),
        ),
    ),
    "schema": Gate(
        name="schema",
        description="Canonical contract schema index gate.",
        kind="command",
        checks=(
            CommandCheck(
                ("bash", "scripts/verify-schema-indexes.sh"),
                "schema index verification",
                required_paths=(Path("scripts/verify-schema-indexes.sh"), Path("contracts/schema-index.json")),
                optional=True,
            ),
        ),
    ),
    "isolation": Gate(
        name="isolation",
        description="Focused tenant isolation security gate.",
        kind="command",
        checks=(
            CommandCheck(
                (
                    sys.executable,
                    "-m",
                    "pytest",
                    "-v",
                    "--tb=short",
                    "tests/security/test_tenant_isolation.py",
                ),
                "tenant isolation pytest",
                required_paths=(Path("tests/security/test_tenant_isolation.py"),),
                optional=True,
            ),
        ),
    ),
    "crawler": Gate(
        name="crawler",
        description="Focused Layer 1 crawler regression gate.",
        kind="command",
        checks=(
            CommandCheck(
                (
                    sys.executable,
                    "-m",
                    "pytest",
                    "-v",
                    "--tb=short",
                    "tests/crawler/",
                    "tests/unit/test_playwright_crawler.py",
                    "tests/unit/test_crawler_config.py",
                    "tests/unit/test_crawler_telemetry.py",
                    "tests/unit/test_quality_gate.py",
                ),
                "layer1 crawler pytest",
                required_paths=(
                    Path("services/layer1-ingestion/tests/crawler"),
                    Path("services/layer1-ingestion/tests/unit/test_playwright_crawler.py"),
                    Path("services/layer1-ingestion/tests/unit/test_crawler_config.py"),
                    Path("services/layer1-ingestion/tests/unit/test_crawler_telemetry.py"),
                    Path("services/layer1-ingestion/tests/unit/test_quality_gate.py"),
                ),
                optional=True,
                cwd=REPO_ROOT / "services/layer1-ingestion",
            ),
        ),
    ),
    "router": Gate(
        name="router",
        description="Router and route contract audit gate.",
        kind="command",
        checks=(
            CommandCheck(
                (sys.executable, "scripts/ci/router_contract_gate.py"),
                "router contract gate",
                required_paths=(Path("scripts/ci/router_contract_gate.py"),),
                optional=True,
            ),
        ),
    ),
    "db-extensions-check": Gate(
        name="db-extensions-check",
        description="Read-only vector store extension/index architecture check.",
        kind="command",
        checks=(
            CommandCheck(
                (sys.executable, "scripts/ci/check_vector_store_health.py"),
                "Layer 3 vector store health check",
                required_paths=(Path("scripts/ci/check_vector_store_health.py"),),
                optional=True,
            ),
        ),
    ),
    "db-migrate-status": Gate(
        name="db-migrate-status",
        description="Read-only database migration status report.",
        kind="command",
        checks=(
            CommandCheck(
                (sys.executable, "scripts/ci/migration_status_report.py", "--mode", "status"),
                "database migration status",
                required_paths=(Path("scripts/ci/migration_status_report.py"),),
                optional=True,
            ),
        ),
    ),
}

ALL_GATE_NAMES = (
    "lint",
    "test",
    "security",
    "schema",
    "isolation",
    "crawler",
    "router",
    "db-extensions-check",
    "db-migrate-status",
)
ALL_GATES = ALL_GATE_NAMES

EXPECTED_CHECKS: dict[str, tuple[PackageCheck, ...]] = {
    name: tuple(check for check in gate.checks if isinstance(check, PackageCheck))
    for name, gate in GATES.items()
    if gate.kind == "package"
}

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


class AggregateCheckError(RuntimeError):
    """Raised when aggregate check configuration or execution fails."""


def _repo_rel(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_package_json(path: Path) -> dict[str, object]:
    package_json = path / "package.json"
    if not package_json.exists():
        raise AggregateCheckError(f"Missing expected package manifest: {package_json}")
    with package_json.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_gate(target: str) -> Gate:
    gate = GATES.get(target)
    if gate is None:
        valid = ", ".join([*sorted(GATES), "all"])
        raise AggregateCheckError(f"Unsupported gate {target!r}; expected one of: {valid}")
    if not gate.checks:
        raise AggregateCheckError(f"Gate {target!r} has zero checks configured")
    return gate


def validate_expected_checks(target: str, repo_root: Path = REPO_ROOT) -> tuple[PackageCheck, ...]:
    if target in EXPECTED_CHECKS:
        checks = EXPECTED_CHECKS[target]
    else:
        gate = get_gate(target)
        checks = tuple(check for check in gate.checks if isinstance(check, PackageCheck))
    if not checks:
        raise AggregateCheckError(f"Aggregate check {target!r} has zero package checks configured")

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


def gate_env() -> dict[str, str]:
    env = os.environ.copy()
    debug = env.get("DEBUG")
    if debug is not None and debug.strip().lower() not in BOOL_STRINGS:
        env["DEBUG"] = "false"
    env.setdefault("PYTHONUTF8", "1")
    temp_dir = REPO_ROOT / ".tmp" / "root-aggregate-temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    env.setdefault("TMP", str(temp_dir))
    env.setdefault("TEMP", str(temp_dir))
    env.setdefault("TMPDIR", str(temp_dir))
    env.setdefault("PYTEST_ADDOPTS", f"-o cache_dir={temp_dir / 'pytest-cache'}")
    if shutil.which("pnpm") is None and shutil.which("corepack") is not None:
        shim_dir = REPO_ROOT / ".tmp" / "root-aggregate-bin"
        shim_dir.mkdir(parents=True, exist_ok=True)
        pnpm_shim = shim_dir / "pnpm.cmd"
        if not pnpm_shim.exists():
            pnpm_shim.write_text("@echo off\r\ncorepack pnpm %*\r\n", encoding="utf-8")
        env["PATH"] = f"{shim_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


def _resolve_command(command: Sequence[str]) -> list[str] | None:
    executable = shutil.which(command[0])
    if command[0] == "bash" and executable is not None and "system32" in executable.lower():
        for git_bash in (
            Path("C:/Program Files/Git/bin/bash.exe"),
            Path("C:/Program Files (x86)/Git/bin/bash.exe"),
            Path("C:/Tools/Git/bin/bash.exe"),
        ):
            if git_bash.exists():
                return [str(git_bash), *command[1:]]
    if executable is not None:
        return [executable, *command[1:]]
    if command[0] == "pnpm":
        corepack = shutil.which("corepack")
        if corepack is not None:
            return [corepack, "pnpm", *command[1:]]
    return None


def default_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    resolved_command = _resolve_command(command)
    if resolved_command is None:
        print(f"Command not found: {command[0]}", file=sys.stderr)
        return subprocess.CompletedProcess(command, 127)
    return subprocess.run(resolved_command, cwd=cwd, env=gate_env(), text=True, check=False)


def capturing_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    resolved_command = _resolve_command(command)
    if resolved_command is None:
        return subprocess.CompletedProcess(command, 127, stdout="", stderr=f"Command not found: {command[0]}\n")
    return subprocess.run(
        resolved_command,
        cwd=cwd,
        env=gate_env(),
        text=True,
        check=False,
        capture_output=True,
    )


def _missing_paths(paths: Sequence[Path], repo_root: Path) -> tuple[str, ...]:
    missing: list[str] = []
    for path in paths:
        candidate = path if path.is_absolute() else repo_root / path
        if not candidate.exists():
            missing.append(_repo_rel(candidate, repo_root))
    return tuple(missing)


def _check_inventory(check: Check, repo_root: Path) -> dict[str, object]:
    if isinstance(check, PackageCheck):
        command = ["pnpm", "--dir", check.package_path, "run", check.script]
        missing_paths = _missing_paths((Path(check.package_path) / "package.json",), repo_root)
        return {
            "label": f"{check.package_path}:{check.script}",
            "command": command,
            "optional": False,
            "status": GateStatus.NOT_RUN.value if not missing_paths else GateStatus.FAILED.value,
            "required_paths": [f"{check.package_path}/package.json"],
            "missing_paths": list(missing_paths),
        }

    missing_paths = _missing_paths(check.required_paths, repo_root)
    status = GateStatus.NOT_APPLICABLE.value if check.optional and missing_paths else GateStatus.NOT_RUN.value
    return {
        "label": check.label,
        "command": list(check.command),
        "optional": check.optional,
        "status": status,
        "required_paths": [path.as_posix() for path in check.required_paths],
        "missing_paths": list(missing_paths),
    }


def gate_registry_json(repo_root: Path = REPO_ROOT) -> dict[str, object]:
    gates = [
        {
            "name": gate.name,
            "description": gate.description,
            "kind": gate.kind,
            "status": GateStatus.NOT_RUN.value,
            "checks": [_check_inventory(check, repo_root) for check in gate.checks],
        }
        for gate in GATES.values()
    ]
    return {
        "gates": gates,
        "aggregate_targets": {"all": list(ALL_GATE_NAMES)},
        "exit_codes": {
            "passed": 0,
            "failed": 1,
            "configuration_error": 2,
            "command_not_found": 127,
            "not_applicable": 0,
        },
        "annotations": [
            {
                "gate": gate["name"],
                "status": gate["status"],
                "message": f"{gate['name']} is registered but was not run",
            }
            for gate in gates
        ],
    }


def _preflight_command_check(check: CommandCheck, repo_root: Path) -> CheckResult | None:
    missing_paths = _missing_paths(check.required_paths, repo_root)
    if not missing_paths:
        return None
    if check.optional:
        return CheckResult(
            label=check.label,
            command=check.command,
            status=GateStatus.NOT_APPLICABLE,
            exit_code=0,
            message="Optional gate prerequisites are not present.",
            missing_paths=missing_paths,
        )
    raise AggregateCheckError(
        f"Gate check {check.label!r} is missing required paths: {', '.join(missing_paths)}"
    )


def _run_package_gate(gate: Gate, repo_root: Path, runner: Runner, emit_text: bool) -> GateResult:
    checks = validate_expected_checks(gate.name, repo_root)
    results: list[CheckResult] = []
    if emit_text:
        print(f"Root aggregate {gate.name}: {len(checks)} package checks planned.")

    for check in checks:
        command = ("pnpm", "--dir", check.package_path, "run", check.script)
        label = f"{check.package_path}:{check.script}"
        if emit_text:
            print(f"\n## {label}")
        result = runner(command, repo_root)
        status = GateStatus.PASSED if result.returncode == 0 else GateStatus.FAILED
        exit_code = 127 if result.returncode == 127 else (0 if result.returncode == 0 else 1)
        results.append(CheckResult(label, command, status, exit_code))

    return _summarize_gate(gate, results, emit_text)


def _run_command_gate(gate: Gate, repo_root: Path, runner: Runner, emit_text: bool) -> GateResult:
    results: list[CheckResult] = []
    command_checks = tuple(check for check in gate.checks if isinstance(check, CommandCheck))
    if emit_text:
        print(f"Root aggregate {gate.name}: {len(command_checks)} command checks planned.")

    for check in command_checks:
        preflight = _preflight_command_check(check, repo_root)
        if preflight is not None:
            results.append(preflight)
            if emit_text:
                print(f"\n## {check.label}")
                print(f"not applicable: {', '.join(preflight.missing_paths)}")
            continue

        actual_cwd = check.cwd if check.cwd.is_absolute() else repo_root / check.cwd
        if emit_text:
            print(f"\n## {check.label}")
        result = runner(check.command, actual_cwd)
        status = GateStatus.PASSED if result.returncode == 0 else GateStatus.FAILED
        exit_code = 127 if result.returncode == 127 else (0 if result.returncode == 0 else 1)
        results.append(CheckResult(check.label, check.command, status, exit_code))

    return _summarize_gate(gate, results, emit_text)


def _summarize_gate(gate: Gate, results: Sequence[CheckResult], emit_text: bool) -> GateResult:
    failed = [result for result in results if result.status == GateStatus.FAILED]
    runnable = [result for result in results if result.status != GateStatus.NOT_APPLICABLE]
    if failed:
        status = GateStatus.FAILED
    elif not runnable:
        status = GateStatus.NOT_APPLICABLE
    else:
        status = GateStatus.PASSED

    exit_code = _exit_code_for_check_results(results)
    if emit_text:
        passed = sum(1 for result in results if result.status == GateStatus.PASSED)
        not_applicable = sum(1 for result in results if result.status == GateStatus.NOT_APPLICABLE)
        print(
            f"\nRoot aggregate {gate.name} summary: {passed} passed, "
            f"{len(failed)} failed, {not_applicable} not_applicable."
        )
        for result in failed:
            print(f" - {result.label} failed with exit code {result.exit_code}", file=sys.stderr)

    return GateResult(gate.name, gate.description, status, exit_code, tuple(results))


def _exit_code_for_check_results(results: Sequence[CheckResult]) -> int:
    if any(result.exit_code == 127 for result in results):
        return 127
    if any(result.status == GateStatus.FAILED for result in results):
        return 1
    return 0


def _exit_code_for_results(results: Sequence[GateResult]) -> int:
    if any(result.exit_code == 127 for result in results):
        return 127
    if any(result.status == GateStatus.FAILED for result in results):
        return 1
    return 0


def run_gate(
    target: str,
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
    *,
    emit_text: bool = True,
) -> GateResult:
    gate = get_gate(target)
    if gate.kind == "package":
        return _run_package_gate(gate, repo_root, runner, emit_text)
    return _run_command_gate(gate, repo_root, runner, emit_text)


def run_aggregate_check(
    target: str,
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
) -> int:
    return run_gate(target, repo_root, runner).exit_code


def run_all(
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
    *,
    emit_text: bool = True,
) -> tuple[GateResult, ...]:
    results: list[GateResult] = []
    for name in ALL_GATE_NAMES:
        if emit_text:
            print(f"\n=== Root aggregate gate: {name} ===")
        results.append(run_gate(name, repo_root, runner, emit_text=emit_text))
    return tuple(results)


def run_gates(
    targets: Sequence[str],
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
) -> list[GateResult]:
    return [run_gate(target, repo_root, runner) for target in targets]


def results_json(results: Sequence[GateResult]) -> dict[str, object]:
    exit_code = _exit_code_for_results(results)
    failed = exit_code != 0
    return {
        "status": GateStatus.FAILED.value if failed else GateStatus.PASSED.value,
        "exit_code": exit_code,
        "gates": [result.to_json() for result in results],
        "annotations": [
            {
                "gate": result.name,
                "status": result.status.value,
                "message": f"{result.name} {result.status.value}",
            }
            for result in results
        ],
    }


def print_gate_list() -> None:
    for name in [*GATES, "all"]:
        print(name)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?")
    parser.add_argument("--list", action="store_true", help="List supported gate names and exit.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable metadata or run results.")
    args = parser.parse_args(argv)

    if args.list:
        print_gate_list()
        return 0

    try:
        if args.target is None:
            if args.json:
                print(json.dumps(gate_registry_json(), indent=2, sort_keys=True))
                return 0
            parser.error("target is required unless --list or --json is provided")

        target = str(args.target)
        runner = capturing_runner if args.json else default_runner
        if target == "all":
            results = run_all(runner=runner, emit_text=not args.json)
        else:
            results = (run_gate(target, runner=runner, emit_text=not args.json),)

        exit_code = _exit_code_for_results(results)
        if args.json:
            print(json.dumps(results_json(results), indent=2, sort_keys=True))
        return exit_code
    except AggregateCheckError as exc:
        if args.json:
            print(
                json.dumps({"status": "configuration_error", "exit_code": 2, "message": str(exc)}, indent=2, sort_keys=True),
                file=sys.stderr,
            )
        else:
            print(f"Root aggregate check configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
