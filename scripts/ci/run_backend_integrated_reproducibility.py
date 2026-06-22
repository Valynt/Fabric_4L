#!/usr/bin/env python3
"""Run and verify backend-integrated J1/J11 reproducibility evidence.

This runner is intentionally narrow. It exercises the local/CI Docker-backed
backend-integrated path documented in
``docs/validation/backend_integrated/backend_integrated_reproducibility_handoff.md``
and verifies retained seed and Playwright artifacts without making launch claims.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "apps" / "web"
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "live-workflow-validation"
DEFAULT_COMPOSE_FILES = [
    REPO_ROOT / "infra" / "compose" / "docker-compose.live.yml",
    REPO_ROOT / ".tmp" / "docker-compose.j11.override.yml",
]
REQUIRED_SERVICES = ["postgres", "redis", "neo4j", "minio", "layer1", "layer4", "frontend"]
CI_RUN_ID_KEYS = ("GITHUB_RUN_ID", "CI_PIPELINE_ID", "BUILD_BUILDID", "BUILDKITE_BUILD_ID")
CI_JOB_URL_KEYS = ("GITHUB_SERVER_URL", "CI_JOB_URL", "BUILD_BUILDURI", "BUILDKITE_BUILD_URL")
STAGING_RUN_ID_KEYS = ("STAGING_EVIDENCE_RUN_ID", "STAGING_DEPLOYMENT_ID", "STAGING_RUN_ID")
STAGING_URL_KEYS = ("STAGING_EVIDENCE_URL", "STAGING_DEPLOYMENT_URL", "STAGING_URL")
SECRET_KEY_PATTERN = re.compile(r"(SECRET|TOKEN|PASSWORD|PASSWD|KEY|AUTH)", re.IGNORECASE)
FLAKE_OUTPUT_PATTERN = re.compile(r"\b(?:flaky|retry|retries|passed on retry)\b", re.IGNORECASE)
SECRET_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("url credentials", re.compile(r"(?i)(postgresql|postgres|mysql|redis|mongodb)://[^\s@]+:[^\s@]+@")),
    ("authorization header", re.compile(r"(?i)(Authorization\s*[:=]\s*)\S+")),
    (
        "secret assignment",
        re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)\s*[=:]\s*\S+"),
    ),
)


class PhaseError(RuntimeError):
    """Raised when a reproducibility phase fails."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_text(text: str) -> str:
    redacted = text
    for _label, pattern in SECRET_VALUE_PATTERNS:
        redacted = pattern.sub(lambda match: match.group(1) + "[REDACTED]" if match.groups() else "[REDACTED]", redacted)
    return redacted


def rel_env_path(path: Path, *, base: Path) -> str:
    return Path(os.path.relpath(path, base)).as_posix()


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PhaseError(f"required JSON artifact is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PhaseError(f"invalid JSON artifact {path}: {exc}") from exc


def parse_junit(path: Path) -> dict[str, int]:
    try:
        root = ElementTree.parse(path).getroot()
    except FileNotFoundError as exc:
        raise PhaseError(f"required JUnit artifact is missing: {path}") from exc
    except ElementTree.ParseError as exc:
        raise PhaseError(f"invalid JUnit XML {path}: {exc}") from exc

    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}

    def add_counts(node: ElementTree.Element) -> None:
        for key in totals:
            value = node.attrib.get(key)
            if value is not None:
                totals[key] += int(float(value))

    if root.tag == "testsuite":
        add_counts(root)
    elif root.tag == "testsuites":
        if any(key in root.attrib for key in totals):
            add_counts(root)
        else:
            for suite in root.findall("testsuite"):
                add_counts(suite)
    else:
        raise PhaseError(f"unsupported JUnit root element in {path}: {root.tag}")

    return totals


def infer_environment(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"):
        return "ci"
    return "local"


def resolve_release_candidate_sha(explicit: str | None, *, evidence_environment: str) -> tuple[str, str]:
    for candidate in (explicit, os.environ.get("RELEASE_CANDIDATE_SHA"), os.environ.get("GITHUB_SHA")):
        if candidate and candidate.strip():
            return candidate.strip(), "explicit_or_environment"

    if evidence_environment in {"ci", "staging"}:
        raise PhaseError(
            "release-candidate SHA is required for CI/staging evidence; "
            "pass --release-candidate-sha or set RELEASE_CANDIDATE_SHA/GITHUB_SHA"
        )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip(), "local_git_rev_parse_tooling_only"
    raise PhaseError(
        "release-candidate SHA is required; pass --release-candidate-sha or set RELEASE_CANDIDATE_SHA/GITHUB_SHA"
    )


def first_nonempty_env(env: dict[str, str], keys: tuple[str, ...]) -> tuple[str | None, str | None]:
    for key in keys:
        value = env.get(key)
        if value and value.strip():
            return key, value.strip()
    return None, None


def validate_approved_environment(
    *,
    args: argparse.Namespace,
    env: dict[str, str],
    evidence_environment: str,
    release_sha_source: str,
) -> dict[str, Any]:
    """Return redacted evidence-environment metadata or fail closed.

    Local runs are allowed for tooling validation, but only CI/staging runs with
    explicit SHA metadata can be reviewed as external reproducibility evidence.
    """

    if evidence_environment == "local":
        return {
            "approvedForGateClosure": False,
            "reason": "local_tooling_only",
        }

    if release_sha_source == "local_git_rev_parse_tooling_only":
        raise PhaseError("CI/staging evidence cannot use local git rev-parse SHA fallback")

    if evidence_environment == "ci":
        ci_marker = env.get("GITHUB_ACTIONS") or env.get("CI")
        run_id_key, run_id = first_nonempty_env(env, CI_RUN_ID_KEYS)
        job_url_key, job_url = first_nonempty_env(env, CI_JOB_URL_KEYS)
        if not ci_marker:
            raise PhaseError("CI evidence requires CI metadata such as CI=true or GITHUB_ACTIONS=true")
        if not run_id:
            raise PhaseError(f"CI evidence requires one run identifier: {', '.join(CI_RUN_ID_KEYS)}")
        return {
            "approvedForGateClosure": True,
            "environment": "ci",
            "ciMarkerPresent": True,
            "runIdKey": run_id_key,
            "runId": run_id,
            "jobUrlKey": job_url_key,
            "jobUrl": job_url,
        }

    if evidence_environment == "staging":
        evidence_run_id = args.evidence_run_id or first_nonempty_env(env, STAGING_RUN_ID_KEYS)[1]
        evidence_url = args.evidence_url or first_nonempty_env(env, STAGING_URL_KEYS)[1]
        if not evidence_run_id:
            raise PhaseError(
                "staging evidence requires --evidence-run-id or one of "
                f"{', '.join(STAGING_RUN_ID_KEYS)}"
            )
        if not evidence_url:
            raise PhaseError(
                "staging evidence requires --evidence-url or one of "
                f"{', '.join(STAGING_URL_KEYS)}"
            )
        return {
            "approvedForGateClosure": True,
            "environment": "staging",
            "evidenceRunId": evidence_run_id,
            "evidenceUrl": evidence_url,
        }

    raise PhaseError(f"unsupported evidence environment: {evidence_environment}")


def base_env(args: argparse.Namespace, artifact_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PLAYWRIGHT_BACKEND_URL": args.backend_url,
            "PLAYWRIGHT_LIVE_MODE": "true",
            "PLAYWRIGHT_LIVE_FRONTEND_URL": args.frontend_url,
            "PLAYWRIGHT_BASE_URL": args.frontend_url,
            "VITE_USE_MOCKS": "false",
            "VITE_ENABLE_MOCK_FALLBACK": "false",
            "E2E_SEED_DATA": "false",
            "SEED_REPORT_JSON": str(artifact_dir / "seed-report.json"),
        }
    )
    env.pop("MSW", None)
    env.pop("MOCKS_ENABLED", None)
    return env


def printable_env_delta(env: dict[str, str]) -> dict[str, str]:
    keys = [
        "PLAYWRIGHT_BACKEND_URL",
        "PLAYWRIGHT_LIVE_MODE",
        "PLAYWRIGHT_LIVE_FRONTEND_URL",
        "PLAYWRIGHT_BASE_URL",
        "VITE_USE_MOCKS",
        "VITE_ENABLE_MOCK_FALLBACK",
        "E2E_SEED_DATA",
        "SEED_REPORT_JSON",
        "SERVICE_AUTH_SECRET",
        "JWT_SECRET",
    ]
    visible: dict[str, str] = {}
    for key in keys:
        if key not in env:
            continue
        visible[key] = "[REDACTED]" if SECRET_KEY_PATTERN.search(key) else env[key]
    visible["MSW"] = "<unset>"
    visible["MOCKS_ENABLED"] = "<unset>"
    visible["CI"] = env.get("CI", "<unset>")
    visible["GITHUB_ACTIONS"] = env.get("GITHUB_ACTIONS", "<unset>")
    visible["GITHUB_RUN_ID"] = env.get("GITHUB_RUN_ID", "<unset>")
    visible["GITHUB_SERVER_URL"] = env.get("GITHUB_SERVER_URL", "<unset>")
    visible["GITHUB_REPOSITORY"] = env.get("GITHUB_REPOSITORY", "<unset>")
    return visible


def run_phase(
    *,
    name: str,
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    phases: list[dict[str, Any]],
) -> str:
    print(f"\n## {name}")
    print("$ " + " ".join(command))
    started = now_iso()
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = redact_text(result.stdout or "")
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    phases.append(
        {
            "name": name,
            "command": command,
            "cwd": str(cwd),
            "startedAt": started,
            "finishedAt": now_iso(),
            "returnCode": result.returncode,
            "retryOrFlakyOutputDetected": bool(FLAKE_OUTPUT_PATTERN.search(output)),
        }
    )
    if result.returncode != 0:
        raise PhaseError(f"{name} failed with exit code {result.returncode}")
    return output


def run_validator_phase(*, name: str, script: str, env: dict[str, str], phases: list[dict[str, Any]]) -> None:
    run_phase(name=name, command=["python", script], cwd=REPO_ROOT, env=env, phases=phases)


def docker_command(compose_files: list[Path]) -> list[str]:
    command = ["docker", "compose"]
    for compose_file in compose_files:
        command.extend(["-f", str(compose_file)])
    command.extend(["up", "-d", "--build", "--wait", *REQUIRED_SERVICES])
    return command


def seed_command() -> tuple[list[str], Path]:
    if is_windows():
        return (
            [
                "cmd",
                "/c",
                r"apps\web\node_modules\.bin\tsx.cmd",
                r"scripts\db\seed-e2e-data.ts",
                "--base-url=http://127.0.0.1:8004",
            ],
            REPO_ROOT,
        )
    return (
        [
            "pnpm",
            "--dir",
            "apps/web",
            "exec",
            "tsx",
            "../../scripts/db/seed-e2e-data.ts",
            "--base-url=http://127.0.0.1:8004",
        ],
        REPO_ROOT,
    )


def playwright_command(specs: list[str]) -> tuple[list[str], Path]:
    if is_windows():
        return (
            ["cmd", "/c", r"node_modules\.bin\playwright.cmd", "test", "--project=backend-integrated", *specs],
            WEB_DIR,
        )
    return (
        ["pnpm", "exec", "playwright", "test", "--project=backend-integrated", *specs],
        WEB_DIR,
    )


def guard_command(mode: str) -> tuple[list[str], Path]:
    return (["node", "apps/web/scripts/live-env-guard.mjs", mode], REPO_ROOT)


def verify_seed(seed_path: Path) -> dict[str, Any]:
    seed = load_json(seed_path)
    aggregate_status = seed.get("aggregateStatus", seed.get("status"))
    required_rows_present = seed.get("requiredRowsPresent")
    if aggregate_status != "present":
        raise PhaseError(f"seed report aggregateStatus/status must be present, got {aggregate_status!r}")
    if required_rows_present is not True:
        raise PhaseError(f"seed report requiredRowsPresent must be true, got {required_rows_present!r}")
    return {"path": str(seed_path), "aggregateStatus": aggregate_status, "requiredRowsPresent": required_rows_present}


def verify_junit(path: Path, *, expected_tests: int | None = None) -> dict[str, Any]:
    counts = parse_junit(path)
    if counts["failures"] != 0 or counts["errors"] != 0:
        raise PhaseError(f"{path} must have failures=0 and errors=0, got {counts}")
    if counts["skipped"] != 0:
        raise PhaseError(f"{path} must have skipped=0, got {counts['skipped']}")
    if expected_tests is not None and counts["tests"] != expected_tests:
        raise PhaseError(f"{path} must have tests={expected_tests}, got {counts['tests']}")
    return {"path": str(path), **counts}


def ensure_under_artifact_dir(path: Path, artifact_dir: Path) -> None:
    resolved = path.resolve()
    root = artifact_dir.resolve()
    if resolved != root and root not in resolved.parents:
        raise PhaseError(f"refusing to reset artifact outside artifact dir: {path}")


def reset_artifacts(paths: list[Path], *, artifact_dir: Path) -> None:
    for path in paths:
        ensure_under_artifact_dir(path, artifact_dir)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def scan_retry_artifacts(output_path: Path) -> list[str]:
    if not output_path.exists():
        return []
    retry_paths: list[str] = []
    for child in output_path.rglob("*"):
        if re.search(r"(?:^|[-_/])retry\d*(?:$|[-_/])", child.as_posix(), re.IGNORECASE):
            retry_paths.append(str(child))
    return sorted(retry_paths)


def evaluate_retry_status(
    *,
    playwright_outputs: list[dict[str, Any]],
    retry_classification: str | None,
) -> dict[str, Any]:
    detections: list[dict[str, Any]] = []
    for item in playwright_outputs:
        output_detected = bool(FLAKE_OUTPUT_PATTERN.search(item.get("output", "")))
        artifact_detected = bool(item.get("retryArtifacts"))
        if output_detected or artifact_detected:
            detections.append(
                {
                    "phase": item["phase"],
                    "outputDetected": output_detected,
                    "retryArtifacts": item.get("retryArtifacts", []),
                }
            )
    status = "none"
    if detections:
        if not retry_classification:
            raise PhaseError(
                "retry/flaky evidence detected but no --retry-classification was provided; "
                "classify the retry before using this as CI/staging evidence"
            )
        status = "classified"
    return {"status": status, "classification": retry_classification, "detections": detections}


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run backend-integrated J1/J11 reproducibility evidence")
    parser.add_argument("--release-candidate-sha", help="Release-candidate commit SHA to record in evidence")
    parser.add_argument(
        "--environment",
        choices=["local", "ci", "staging"],
        help="Execution environment. Local runs are recorded as TOOLING_ONLY and cannot close CI/staging evidence.",
    )
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR), help="Artifact root")
    parser.add_argument("--frontend-url", default="http://localhost:3001", help="Frontend URL for Playwright")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8004", help="Layer 4 backend URL for seeding")
    parser.add_argument(
        "--compose-file",
        action="append",
        dest="compose_files",
        help="Docker compose file. Can be provided multiple times.",
    )
    parser.add_argument("--skip-stack-start", action="store_true", help="Use an already-running approved stack")
    parser.add_argument(
        "--evidence-run-id",
        help="Required staging evidence run/deployment identifier unless provided by staging environment variables.",
    )
    parser.add_argument(
        "--evidence-url",
        help="Required staging evidence/deployment URL unless provided by staging environment variables.",
    )
    parser.add_argument(
        "--retry-classification",
        help="Required when Playwright reports a retry/flaky result; recorded without hiding residual risk.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    artifact_dir = Path(args.artifact_dir)
    if not artifact_dir.is_absolute():
        artifact_dir = REPO_ROOT / artifact_dir
    artifact_dir = artifact_dir.resolve()
    playwright_dir = artifact_dir / "playwright"
    summary_path = artifact_dir / "backend-integrated-reproducibility-summary.json"
    compose_files = [Path(p).resolve() for p in args.compose_files] if args.compose_files else DEFAULT_COMPOSE_FILES
    evidence_environment = infer_environment(args.environment)
    phases: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "generatedAt": now_iso(),
        "status": "FAIL",
        "releaseCandidateSha": None,
        "releaseCandidateShaSource": None,
        "evidenceEnvironment": evidence_environment,
        "evidenceScope": "TOOLING_ONLY" if evidence_environment == "local" else "CI_STAGING_CANDIDATE",
        "artifactDir": str(artifact_dir),
        "frontendUrl": args.frontend_url,
        "backendUrl": args.backend_url,
        "composeFiles": [str(path) for path in compose_files],
        "requiredServices": REQUIRED_SERVICES,
        "skipStackStart": args.skip_stack_start,
        "approvedEnvironment": {"approvedForGateClosure": False, "reason": "not_evaluated"},
        "environment": {},
        "phases": phases,
        "artifacts": {},
        "retryFlakeStatus": {"status": "not_evaluated"},
        "validatorStatus": {"status": "not_run"},
    }

    try:
        release_sha, release_sha_source = resolve_release_candidate_sha(
            args.release_candidate_sha, evidence_environment=evidence_environment
        )
        env = base_env(args, artifact_dir)
        summary["releaseCandidateSha"] = release_sha
        summary["releaseCandidateShaSource"] = release_sha_source
        summary["environment"] = printable_env_delta(env)
        summary["approvedEnvironment"] = validate_approved_environment(
            args=args,
            env=env,
            evidence_environment=evidence_environment,
            release_sha_source=release_sha_source,
        )
        artifact_dir.mkdir(parents=True, exist_ok=True)
        playwright_dir.mkdir(parents=True, exist_ok=True)

        if not args.skip_stack_start:
            run_phase(name="start docker-backed stack", command=docker_command(compose_files), cwd=REPO_ROOT, env=env, phases=phases)

        command, cwd = guard_command("seed")
        run_phase(name="verify seed guard", command=command, cwd=cwd, env=env, phases=phases)

        command, cwd = seed_command()
        run_phase(name="seed backend-integrated validation data", command=command, cwd=cwd, env=env, phases=phases)

        summary["artifacts"]["seedReport"] = verify_seed(artifact_dir / "seed-report.json")

        runs = [
            (
                "run J1-only backend-integrated Playwright",
                ["e2e/journeys/j1-golden-path-backend-integrated.spec.ts"],
                playwright_dir / "j1-junit.xml",
                playwright_dir / "j1-html",
                playwright_dir / "j1-test-results",
                None,
                "j1Junit",
            ),
            (
                "run J11-only backend-integrated Playwright",
                ["e2e/journeys/j11-golden-path-business-lifecycle.spec.ts"],
                playwright_dir / "j11-junit.xml",
                playwright_dir / "j11-html",
                playwright_dir / "j11-test-results",
                None,
                "j11Junit",
            ),
            (
                "run J1+J11 backend-integrated Playwright pair",
                [
                    "e2e/journeys/j1-golden-path-backend-integrated.spec.ts",
                    "e2e/journeys/j11-golden-path-business-lifecycle.spec.ts",
                ],
                playwright_dir / "junit.xml",
                playwright_dir / "html",
                playwright_dir / "test-results",
                20,
                "pairJunit",
            ),
        ]

        playwright_outputs: list[dict[str, Any]] = []
        for name, specs, junit_path, html_path, output_path, expected_tests, artifact_key in runs:
            reset_artifacts([junit_path, html_path, output_path], artifact_dir=artifact_dir)
            run_env = env.copy()
            run_env.update(
                {
                    "PLAYWRIGHT_JUNIT_FILE": rel_env_path(junit_path, base=WEB_DIR),
                    "PLAYWRIGHT_HTML_REPORT": rel_env_path(html_path, base=WEB_DIR),
                    "PLAYWRIGHT_OUTPUT_DIR": rel_env_path(output_path, base=WEB_DIR),
                }
            )
            command, cwd = guard_command("test")
            run_phase(name=f"{name} guard", command=command, cwd=cwd, env=run_env, phases=phases)
            command, cwd = playwright_command(specs)
            output = run_phase(name=name, command=command, cwd=cwd, env=run_env, phases=phases)
            playwright_outputs.append(
                {
                    "phase": name,
                    "output": output,
                    "retryArtifacts": scan_retry_artifacts(output_path),
                }
            )
            summary["artifacts"][artifact_key] = verify_junit(junit_path, expected_tests=expected_tests)

        summary["retryFlakeStatus"] = evaluate_retry_status(
            playwright_outputs=playwright_outputs,
            retry_classification=args.retry_classification,
        )
        summary["validatorStatus"] = {"status": "RUNNING"}
        run_validator_phase(
            name="validate core GA launch evidence",
            script="scripts/ci/validate_core_ga_launch_evidence.py",
            env=env,
            phases=phases,
        )
        run_validator_phase(
            name="validate final testing launch gate",
            script="scripts/ci/validate_final_testing_launch_gate.py",
            env=env,
            phases=phases,
        )
        summary["validatorStatus"] = {"status": "PASS"}
        summary["status"] = "PASS"
        if summary["retryFlakeStatus"]["status"] == "classified":
            summary["status"] = "PASS_WITH_CLASSIFIED_RETRY"
        if evidence_environment == "local":
            summary["status"] = "TOOLING_ONLY_PASS"
        print("\n## Evidence summary")
        print(json.dumps(summary["artifacts"], indent=2, sort_keys=True))
        return 0
    except PhaseError as exc:
        summary["error"] = str(exc)
        if any(phase["name"].startswith("validate ") and phase["returnCode"] != 0 for phase in phases):
            summary["validatorStatus"] = {"status": "FAIL"}
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        summary["finishedAt"] = now_iso()
        write_summary(summary_path, summary)
        print(f"\nWrote summary: {summary_path}")


if __name__ == "__main__":
    raise SystemExit(main())
