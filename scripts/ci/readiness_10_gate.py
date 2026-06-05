#!/usr/bin/env python3
"""Run the fail-closed 10/10 repository readiness gate."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "readiness-10"
SUMMARY_JSON = "readiness-10-summary.json"
SUMMARY_MD = "readiness-10-summary.md"

REQUIRED_ROOT_SCRIPTS: dict[str, str] = {
    "readiness:10": "python scripts/ci/readiness_10_gate.py",
    "test:schema": "python scripts/ci/run_root_aggregate_checks.py schema",
    "contract:breaking": "python scripts/ci/openapi_breaking_change_gate.py",
    "db:migrate:status": "python scripts/ci/run_root_aggregate_checks.py db-migrate-status",
    "test:security": "python -m pytest tests/security/ -v --tb=short",
    "test:isolation": "python scripts/ci/run_root_aggregate_checks.py isolation",
    "test:router": "python scripts/ci/run_root_aggregate_checks.py router",
}


@dataclass(frozen=True)
class GateCommand:
    command: tuple[str, ...]
    label: str


@dataclass(frozen=True)
class GateDimension:
    key: str
    name: str
    commands: tuple[GateCommand, ...] = ()
    static_check: str | None = None


@dataclass(frozen=True)
class GateResult:
    key: str
    name: str
    status: str
    exit_code: int
    commands: tuple[dict[str, object], ...]
    summary: str


CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


READINESS_DIMENSIONS: tuple[GateDimension, ...] = (
    GateDimension("script_parity", "Root pnpm script parity", static_check="root_script_parity"),
    GateDimension(
        "schema_index",
        "Schema index verification",
        (GateCommand(("pnpm", "test:schema"), "pnpm test:schema"),),
    ),
    GateDimension(
        "openapi_breaking_change",
        "OpenAPI breaking-change check",
        (GateCommand(("pnpm", "contract:breaking"), "pnpm contract:breaking"),),
    ),
    GateDimension(
        "migration_status",
        "Migration status",
        (GateCommand(("pnpm", "db:migrate:status"), "pnpm db:migrate:status"),),
    ),
    GateDimension(
        "security_suite",
        "Security suite",
        (GateCommand(("pnpm", "test:security"), "pnpm test:security"),),
    ),
    GateDimension(
        "tenant_isolation_suite",
        "Tenant isolation suite",
        (GateCommand(("pnpm", "test:isolation"), "pnpm test:isolation"),),
    ),
    GateDimension(
        "router_gate",
        "Router gate",
        (GateCommand(("pnpm", "test:router"), "pnpm test:router"),),
    ),
    GateDimension(
        "ci_workflow_registry",
        "CI workflow registry",
        (
            GateCommand(
                (sys.executable, "scripts/ci/verify_workflow_registry.py"),
                "workflow registry",
            ),
        ),
    ),
    GateDimension(
        "evidence_bundle_generation",
        "Evidence bundle generation",
        (
            GateCommand(
                (sys.executable, "scripts/ci/generate_release_evidence_packet.py", "--allow-placeholder-sha"),
                "release evidence packet",
            ),
        ),
    ),
    GateDimension(
        "maturity_scorecard_threshold",
        "Maturity scorecard threshold",
        (
            GateCommand(
                (sys.executable, "scripts/reports/generate_repo_maturity_scorecard.py", "--min-score", "10"),
                "repo maturity scorecard",
            ),
        ),
    ),
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _tail(text: str, limit: int = 1500) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def default_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    except FileNotFoundError:
        return subprocess.CompletedProcess(command, 127, "", f"command not found: {command[0] if command else ''}")


def _resolve_command(command: Sequence[str]) -> tuple[str, ...]:
    if not command:
        return ()
    if command[0] == "pnpm" and shutil.which("pnpm") is None and shutil.which("corepack") is not None:
        corepack = shutil.which("corepack") or "corepack"
        return (corepack, "pnpm", *command[1:])
    executable = shutil.which(command[0])
    if executable is not None:
        return (executable, *command[1:])
    return tuple(command)


def _script_parity() -> GateResult:
    package_path = REPO_ROOT / "package.json"
    commands: list[dict[str, object]] = [
        {
            "label": "root package script parity",
            "command": f"read {package_path.relative_to(REPO_ROOT).as_posix()}",
            "exit_code": 0,
            "output_tail": "",
        }
    ]

    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI should report concise parity failure.
        commands[0]["exit_code"] = 1
        commands[0]["output_tail"] = f"failed to read package.json: {exc}"
        return GateResult("script_parity", "Root pnpm script parity", "failed", 1, tuple(commands), str(commands[0]["output_tail"]))

    scripts = package.get("scripts")
    failures: list[str] = []
    if not isinstance(scripts, dict):
        failures.append("package.json scripts must be an object")
    else:
        for name, expected in REQUIRED_ROOT_SCRIPTS.items():
            actual = scripts.get(name)
            if actual != expected:
                failures.append(f"{name}: expected {expected!r}, got {actual!r}")

    if failures:
        commands[0]["exit_code"] = 1
        commands[0]["output_tail"] = "; ".join(failures)
        return GateResult("script_parity", "Root pnpm script parity", "failed", 1, tuple(commands), "; ".join(failures))

    return GateResult(
        "script_parity",
        "Root pnpm script parity",
        "passed",
        0,
        tuple(commands),
        f"{len(REQUIRED_ROOT_SCRIPTS)} root package scripts match canonical commands.",
    )


def run_dimension(dimension: GateDimension, runner: CommandRunner = default_runner) -> GateResult:
    if dimension.static_check == "root_script_parity":
        return _script_parity()

    command_results: list[dict[str, object]] = []
    failures: list[str] = []
    for command in dimension.commands:
        resolved_command = _resolve_command(command.command)
        executable = shutil.which(resolved_command[0]) if resolved_command else None
        if resolved_command and executable is None and resolved_command[0] not in {sys.executable}:
            completed = subprocess.CompletedProcess(resolved_command, 127, "", f"command not found: {resolved_command[0]}")
        else:
            completed = runner(resolved_command, REPO_ROOT)

        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        command_result = {
            "label": command.label,
            "command": " ".join(resolved_command),
            "exit_code": completed.returncode,
            "output_tail": _tail(output),
        }
        command_results.append(command_result)
        if completed.returncode != 0:
            failures.append(f"{command.label} exited {completed.returncode}")

    status = "passed" if not failures else "failed"
    exit_code = 0 if not failures else 1
    summary = "all commands passed" if not failures else "; ".join(failures)
    return GateResult(dimension.key, dimension.name, status, exit_code, tuple(command_results), summary)


def _summary_payload(results: Sequence[GateResult], artifact_dir: Path, *, final: bool) -> dict[str, object]:
    failures = [result for result in results if result.status != "passed"]
    return {
        "generated_at_utc": _utc_now(),
        "gate": "readiness:10",
        "status": "PASS" if not failures and final else "FAIL",
        "final": final,
        "artifact_dir": _display_path(artifact_dir),
        "passed": sum(result.status == "passed" for result in results),
        "failed": len(failures),
        "total": len(results),
        "results": [asdict(result) for result in results],
        "failure_summary": [f"{result.name}: {result.summary}" for result in failures],
    }


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# 10/10 Readiness Gate",
        "",
        f"- Generated at: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status']}**",
        f"- Passed: {payload['passed']}/{payload['total']}",
        "",
        "| Dimension | Status | Summary |",
        "|---|---|---|",
    ]
    for result in payload["results"]:  # type: ignore[index]
        assert isinstance(result, dict)
        status = "PASS" if result["status"] == "passed" else "FAIL"
        lines.append(f"| {result['name']} | {status} | {result['summary']} |")

    failures = payload.get("failure_summary") or []
    if failures:
        lines.extend(["", "## Failure Summary", ""])
        for failure in failures:
            lines.append(f"- {failure}")
    lines.append("")
    return "\n".join(lines)


def write_artifacts(results: Sequence[GateResult], artifact_dir: Path, *, final: bool) -> dict[str, object]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = _summary_payload(results, artifact_dir, final=final)
    (artifact_dir / SUMMARY_JSON).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (artifact_dir / SUMMARY_MD).write_text(_render_markdown(payload), encoding="utf-8")
    return payload


def run_readiness_gate(
    *,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    runner: CommandRunner = default_runner,
    dimensions: Sequence[GateDimension] = READINESS_DIMENSIONS,
) -> int:
    results: list[GateResult] = []
    for dimension in dimensions:
        if dimension.key == "maturity_scorecard_threshold":
            write_artifacts(results, artifact_dir, final=False)
            dimension = GateDimension(
                dimension.key,
                dimension.name,
                (
                    GateCommand(
                        (
                            sys.executable,
                            "scripts/reports/generate_repo_maturity_scorecard.py",
                            "--min-score",
                            "10",
                            "--readiness-summary",
                            _display_path(artifact_dir / SUMMARY_JSON),
                            "--artifact-dir",
                            _display_path(artifact_dir),
                        ),
                        "repo maturity scorecard",
                    ),
                ),
            )
        result = run_dimension(dimension, runner)
        results.append(result)

    payload = write_artifacts(results, artifact_dir, final=True)
    print(_render_markdown(payload))
    return 0 if payload["status"] == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else REPO_ROOT / args.artifact_dir
    return run_readiness_gate(artifact_dir=artifact_dir)


if __name__ == "__main__":
    raise SystemExit(main())
