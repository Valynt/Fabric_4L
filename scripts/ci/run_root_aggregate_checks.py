#!/usr/bin/env python3
"""Fail-closed root aggregate package and governance checks.

The root package scripts must not pass when pnpm selects zero package scripts.
This runner keeps the expected workspace checks explicit and verifies every
package/script pair before invoking pnpm. Governance gates such as crawler use
explicit command matrices so CI can distinguish active coverage from an
intentional, machine-readable non-applicability decision.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CRAWLER_DECISION_PATH = Path("config/ci/crawler-capability-decision.json")


@dataclass(frozen=True)
class PackageCheck:
    package_path: str
    script: str


@dataclass(frozen=True)
class CommandCheck:
    key: str
    description: str
    command: tuple[str, ...]


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

EXPECTED_COMMAND_CHECKS: dict[str, tuple[CommandCheck, ...]] = {
    "crawler": (
        CommandCheck(
            "crawler_unit_tests",
            "Crawler router, quality-gate, and configuration unit tests",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "services/layer1-ingestion/tests/crawler/test_quality_gate.py",
                "services/layer1-ingestion/tests/crawler/test_smart_router.py",
                "services/layer1-ingestion/tests/unit/test_crawler_config.py",
                "services/layer1-ingestion/tests/unit/test_smart_router.py",
            ),
        ),
        CommandCheck(
            "crawler_robots_allowlist_policy_tests",
            "Robots, URL allowlist/SSRF, and browser-boundary policy tests",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "services/layer1-ingestion/tests/unit/test_robots_checker_modes.py",
                "services/layer1-ingestion/tests/security/test_url_safety_hostile.py",
                "services/layer1-ingestion/tests/security/test_layer1_browser_ssrf_guard.py",
            ),
        ),
        CommandCheck(
            "crawler_rate_limit_tests",
            "Layer 1 crawler/API rate-limit enforcement tests",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "services/layer1-ingestion/tests/test_rate_limit_enforcement.py",
            ),
        ),
        CommandCheck(
            "crawler_extraction_boundary_tests",
            "Crawler-to-extraction content boundary tests",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "services/layer1-ingestion/tests/unit/test_content_extractor.py",
            ),
        ),
        CommandCheck(
            "crawler_tenant_safe_ingestion_tests",
            "Tenant-safe ingestion propagation and hostile cross-tenant tests",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "services/layer1-ingestion/tests/test_cross_tenant_hostile.py",
                "services/layer1-ingestion/tests/test_api_tenant_propagation.py",
            ),
        ),
    ),
}

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


class AggregateCheckError(RuntimeError):
    """Raised when aggregate check configuration or execution fails."""


def _load_package_json(path: Path) -> dict[str, object]:
    package_json = path / "package.json"
    if not package_json.exists():
        raise AggregateCheckError(f"Missing expected package manifest: {package_json}")
    with package_json.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise AggregateCheckError(f"Missing required governance decision file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise AggregateCheckError(f"Governance decision file must contain a JSON object: {path}")
    return data


def validate_expected_checks(target: str, repo_root: Path = REPO_ROOT) -> tuple[PackageCheck, ...]:
    checks = EXPECTED_CHECKS.get(target)
    if checks is None:
        valid = ", ".join(sorted((*EXPECTED_CHECKS, *EXPECTED_COMMAND_CHECKS)))
        raise AggregateCheckError(f"Unsupported aggregate check {target!r}; expected one of: {valid}")
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


def validate_command_checks(target: str, repo_root: Path = REPO_ROOT) -> tuple[CommandCheck, ...]:
    checks = EXPECTED_COMMAND_CHECKS.get(target)
    if checks is None:
        valid = ", ".join(sorted((*EXPECTED_CHECKS, *EXPECTED_COMMAND_CHECKS)))
        raise AggregateCheckError(f"Unsupported aggregate check {target!r}; expected one of: {valid}")
    if not checks:
        raise AggregateCheckError(f"Aggregate check {target!r} has zero command checks configured")

    for check in checks:
        if not check.command:
            raise AggregateCheckError(f"Command check {check.key!r} has no command configured")
        if shutil.which(check.command[0]) is None:
            raise AggregateCheckError(
                f"Command check {check.key!r} references missing executable {check.command[0]!r}"
            )
        for argument in check.command[1:]:
            if argument.startswith("-") or argument in {"python", "pytest"}:
                continue
            if argument.endswith(".py") or "/" in argument:
                path = repo_root / argument
                if not path.exists():
                    raise AggregateCheckError(
                        f"Command check {check.key!r} references missing path: {argument}"
                    )
    return checks


def validate_crawler_decision(repo_root: Path = REPO_ROOT) -> dict[str, object]:
    decision = _load_json(repo_root / CRAWLER_DECISION_PATH)
    status = decision.get("status")
    if status not in {"active", "not_applicable"}:
        raise AggregateCheckError(
            f"Crawler capability decision status must be 'active' or 'not_applicable': {CRAWLER_DECISION_PATH}"
        )

    crawler_roots = decision.get("crawler_roots")
    if status == "active":
        if not isinstance(crawler_roots, list) or not crawler_roots:
            raise AggregateCheckError("Active crawler decision requires non-empty crawler_roots")
        missing = [root for root in crawler_roots if not isinstance(root, str) or not (repo_root / root).exists()]
        if missing:
            raise AggregateCheckError(f"Active crawler decision references missing crawler roots: {missing}")
    else:
        required = ("reason", "owner", "review_by", "scorecard_resolution")
        missing_keys = [key for key in required if not decision.get(key)]
        if missing_keys:
            raise AggregateCheckError(
                f"Crawler not_applicable decision missing required keys: {', '.join(missing_keys)}"
            )
    return decision


def default_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    executable = shutil.which(command[0])
    if executable is None:
        return subprocess.CompletedProcess(command, 127, "", f"Command not found: {command[0]}\n")
    resolved_command = [executable, *command[1:]]
    return subprocess.run(
        resolved_command,
        cwd=cwd,
        text=True,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _emit_completed_process_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def _json_report(target: str, status: str, planned: int, passed: int, results: list[dict[str, object]]) -> dict[str, object]:
    return {
        "target": target,
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "planned_checks": planned,
        "passed_checks": passed,
        "failed_checks": planned - passed,
        "checks": results,
    }


def run_aggregate_check(
    target: str,
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
    *,
    emit_json: bool = False,
) -> int:
    if target in EXPECTED_COMMAND_CHECKS:
        return run_command_check(target, repo_root, runner, emit_json=emit_json)

    checks = validate_expected_checks(target, repo_root)
    if not emit_json:
        print(f"Root aggregate {target}: {len(checks)} package checks planned.")

    failures: list[tuple[PackageCheck, int]] = []
    results: list[dict[str, object]] = []
    for check in checks:
        command = ["pnpm", "--dir", check.package_path, "run", check.script]
        if not emit_json:
            print(f"\n## {check.package_path}:{check.script}")
        result = runner(command, repo_root)
        if not emit_json:
            _emit_completed_process_output(result)
        passed = result.returncode == 0
        if not passed:
            failures.append((check, result.returncode))
        results.append(
            {
                "key": f"{check.package_path}:{check.script}",
                "command": command,
                "status": "pass" if passed else "fail",
                "returncode": result.returncode,
                "stdout": result.stdout if emit_json else None,
                "stderr": result.stderr if emit_json else None,
            }
        )

    passed_count = len(checks) - len(failures)
    if emit_json:
        print(json.dumps(_json_report(target, "pass" if not failures else "fail", len(checks), passed_count, results), indent=2))
    else:
        print(f"\nRoot aggregate {target} summary: {passed_count} passed, {len(failures)} failed.")
        if failures:
            for check, returncode in failures:
                print(
                    f" - {check.package_path}:{check.script} failed with exit code {returncode}",
                    file=sys.stderr,
                )
            return 1
    return 0 if not failures else 1


def run_command_check(
    target: str,
    repo_root: Path = REPO_ROOT,
    runner: Runner = default_runner,
    *,
    emit_json: bool = False,
) -> int:
    if target == "crawler":
        decision = validate_crawler_decision(repo_root)
        if decision["status"] == "not_applicable":
            report = _json_report(
                target,
                "not_applicable",
                0,
                0,
                [
                    {
                        "key": "crawler_non_applicability_contract",
                        "status": "not_applicable",
                        "decision_file": str(CRAWLER_DECISION_PATH),
                        "reason": decision.get("reason"),
                        "scorecard_resolution": decision.get("scorecard_resolution"),
                    }
                ],
            )
            if emit_json:
                print(json.dumps(report, indent=2))
            else:
                print("Crawler capability is intentionally not applicable.")
                print(f"Decision file: {CRAWLER_DECISION_PATH}")
                print(f"Reason: {decision.get('reason')}")
            return 0

    checks = validate_command_checks(target, repo_root)
    if not emit_json:
        print(f"Root aggregate {target}: {len(checks)} command checks planned.")

    failures: list[tuple[CommandCheck, int]] = []
    results: list[dict[str, object]] = []
    for check in checks:
        command = list(check.command)
        if not emit_json:
            print(f"\n## {check.key}")
            print("$ " + " ".join(command))
        result = runner(command, repo_root)
        if not emit_json:
            _emit_completed_process_output(result)
        passed = result.returncode == 0
        if not passed:
            failures.append((check, result.returncode))
        results.append(
            {
                "key": check.key,
                "description": check.description,
                "command": command,
                "status": "pass" if passed else "fail",
                "returncode": result.returncode,
                "stdout": result.stdout if emit_json else None,
                "stderr": result.stderr if emit_json else None,
            }
        )

    passed_count = len(checks) - len(failures)
    if emit_json:
        print(json.dumps(_json_report(target, "pass" if not failures else "fail", len(checks), passed_count, results), indent=2))
    else:
        print(f"\nRoot aggregate {target} summary: {passed_count} passed, {len(failures)} failed.")
        if failures:
            for check, returncode in failures:
                print(f" - {check.key} failed with exit code {returncode}", file=sys.stderr)
            return 1
    return 0 if not failures else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=sorted((*EXPECTED_CHECKS, *EXPECTED_COMMAND_CHECKS)))
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable check report")
    args = parser.parse_args(argv)

    try:
        return run_aggregate_check(args.target, emit_json=args.json)
    except AggregateCheckError as exc:
        if args.json:
            print(json.dumps({"target": args.target, "status": "configuration_error", "error": str(exc)}, indent=2))
        else:
            print(f"Root aggregate check configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
