#!/usr/bin/env python3
"""Generate a canonical repository-owned release evidence packet.

This script aggregates the existing readiness validators into one machine-readable
packet and a concise markdown summary. It intentionally stops at repository-owned
evidence and does not claim live-environment production PASS.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "docs/launch/evidence-manifest.example.yaml"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts/release/evidence-packet"
DEFAULT_PRODUCTION_READINESS_MANIFEST = ROOT / "artifacts/production-readiness/manifest.json"


@dataclass(frozen=True)
class ValidatorResult:
    name: str
    passed: bool
    command: list[str]
    detail: str


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_validator(name: str, command: list[str]) -> ValidatorResult:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part).strip()
    detail = output[-1500:] if output else "completed"
    return ValidatorResult(
        name=name,
        passed=result.returncode == 0,
        command=command,
        detail=detail,
    )


def _resolve_release_sha(explicit_sha: str | None) -> str:
    if explicit_sha:
        return explicit_sha

    for key in ("RELEASE_SHA", "GITHUB_SHA", "CI_COMMIT_SHA"):
        value = os.environ.get(key)
        if value:
            return value

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _load_manifest(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("manifest root must be a mapping")
    return loaded


def _load_json_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} root must be a JSON object")
    return loaded


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _validate_manifest_sha(manifest: dict[str, Any], release_sha: str, allow_placeholder_sha: bool) -> None:
    manifest_sha = str(manifest.get("release_candidate_sha", "")).strip()
    if not manifest_sha:
        raise ValueError("manifest release_candidate_sha is required")
    if manifest_sha == release_sha:
        return
    if allow_placeholder_sha and manifest_sha == "REPLACE_WITH_COMMIT_SHA":
        return
    raise ValueError(
        f"manifest release_candidate_sha={manifest_sha!r} does not match release SHA {release_sha!r}"
    )


def _build_packet(
    release_sha: str,
    manifest_path: Path,
    manifest: dict[str, Any],
    production_readiness_manifest_path: Path,
    production_readiness_manifest: dict[str, Any] | None,
    validators: list[ValidatorResult],
) -> dict[str, Any]:
    gate_statuses = {
        gate_name: gate.get("status")
        for gate_name, gate in (manifest.get("gates") or {}).items()
        if isinstance(gate, dict)
    }
    production_readiness = _production_readiness_summary(
        production_readiness_manifest_path,
        production_readiness_manifest,
    )
    validators = [
        *validators,
        _production_readiness_authorization_result(production_readiness),
    ]
    return {
        "generated_at_utc": _utc_now(),
        "release_sha": release_sha,
        "manifest_path": _display_path(manifest_path),
        "overall_status": "PASS" if all(result.passed for result in validators) else "FAIL",
        "repository_scope_note": (
            "This packet proves repository-owned readiness only. "
            "Live-environment evidence is still required for production PASS."
        ),
        "validators": [asdict(result) for result in validators],
        "launch_evidence_gate_statuses": gate_statuses,
        "production_readiness_gate": production_readiness,
    }


def _production_readiness_summary(
    manifest_path: Path,
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    if manifest is None:
        return {
            "manifest_path": _display_path(manifest_path),
            "manifest_found": False,
            "overall_status": "missing",
            "gate_scope": None,
            "release_authorizing": False,
            "covered_regression_domains": [],
            "required_regression_domains": [],
            "suites": [],
        }

    suites = []
    for suite in manifest.get("suites", []):
        if not isinstance(suite, dict):
            continue
        suites.append(
            {
                "suite": suite.get("suite"),
                "status": suite.get("status"),
                "blocking": suite.get("blocking"),
                "regression_domains": suite.get("regression_domains", []),
                "junit_artifact": suite.get("junit_artifact"),
                "summary_artifact": suite.get("summary_artifact"),
            }
        )

    return {
        "manifest_path": _display_path(manifest_path),
        "manifest_found": True,
        "overall_status": manifest.get("overall_status"),
        "gate_scope": manifest.get("gate_scope"),
        "release_authorizing": bool(manifest.get("release_authorizing")),
        "covered_regression_domains": manifest.get("covered_regression_domains", []),
        "required_regression_domains": manifest.get("required_regression_domains", []),
        "suites": suites,
    }


def _production_readiness_authorization_result(production_readiness: dict[str, Any]) -> ValidatorResult:
    if production_readiness["release_authorizing"] is True:
        return ValidatorResult(
            name="production_readiness_release_authorization",
            passed=True,
            command=["internal:production_readiness_release_authorization"],
            detail="production-readiness manifest is full and release-authorizing",
        )

    return ValidatorResult(
        name="production_readiness_release_authorization",
        passed=False,
        command=["internal:production_readiness_release_authorization"],
        detail=(
            "production-readiness manifest is not release-authorizing "
            f"(found={production_readiness['manifest_found']}, "
            f"scope={production_readiness['gate_scope']}, "
            f"status={production_readiness['overall_status']})"
        ),
    )


def _render_summary(packet: dict[str, Any]) -> str:
    validators: list[dict[str, Any]] = packet["validators"]
    lines = [
        "# Release Evidence Packet",
        "",
        f"- Generated at: `{packet['generated_at_utc']}`",
        f"- Release SHA: `{packet['release_sha']}`",
        f"- Manifest: `{packet['manifest_path']}`",
        f"- Overall status: **{packet['overall_status']}**",
        "",
        "## Validator Results",
        "",
    ]

    for validator in validators:
        status = "PASS" if validator["passed"] else "FAIL"
        lines.append(f"- `{status}` `{validator['name']}`")

    lines.extend(
        [
            "",
            "## Launch Evidence Gates",
            "",
        ]
    )

    gate_statuses: dict[str, Any] = packet["launch_evidence_gate_statuses"]
    for gate_name in sorted(gate_statuses):
        lines.append(f"- `{gate_name}`: `{gate_statuses[gate_name]}`")

    production_readiness = packet["production_readiness_gate"]
    lines.extend(
        [
            "",
            "## Production Readiness Gate",
            "",
            f"- Manifest: `{production_readiness['manifest_path']}`",
            f"- Manifest found: `{production_readiness['manifest_found']}`",
            f"- Overall status: `{production_readiness['overall_status']}`",
            f"- Gate scope: `{production_readiness['gate_scope']}`",
            f"- Release authorizing: `{production_readiness['release_authorizing']}`",
            "- Covered regression domains: "
            + ", ".join(f"`{domain}`" for domain in production_readiness["covered_regression_domains"]),
            "",
        ]
    )

    lines.extend(
        [
            "",
            "## Scope Boundary",
            "",
            packet["repository_scope_note"],
            "",
        ]
    )
    return "\n".join(lines)


def _load_manifest_validator() -> Any:
    validator_path = ROOT / "scripts/ci/validate_launch_evidence_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_launch_evidence_manifest", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load manifest validator from {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_manifest


def generate_release_evidence_packet(
    *,
    manifest_path: Path,
    production_readiness_manifest_path: Path,
    output_dir: Path,
    release_sha: str | None,
    allow_placeholder_sha: bool,
) -> int:
    resolved_sha = _resolve_release_sha(release_sha)
    manifest = _load_manifest(manifest_path)
    _validate_manifest_sha(manifest, resolved_sha, allow_placeholder_sha)

    validate_manifest = _load_manifest_validator()
    manifest_errors = validate_manifest(manifest_path)
    if manifest_errors:
        raise ValueError("; ".join(manifest_errors))
    production_readiness_manifest = _load_json_manifest(production_readiness_manifest_path)

    validators = [
        _run_validator(
            "launch_evidence_manifest",
            [sys.executable, "scripts/ci/validate_launch_evidence_manifest.py", _display_path(manifest_path)],
        ),
        _run_validator(
            "production_readiness_manifest",
            [
                sys.executable,
                "scripts/ci/validate_production_readiness_manifest.py",
                _display_path(production_readiness_manifest_path),
            ],
        ),
        _run_validator(
            "final_testing_launch_gate",
            [sys.executable, "scripts/ci/validate_final_testing_launch_gate.py"],
        ),
        _run_validator(
            "production_readiness_plan",
            [sys.executable, "scripts/ci/validate_production_readiness_plan.py"],
        ),
        _run_validator(
            "platform_contract_lint",
            [sys.executable, "scripts/ci/platform_contract_lint.py"],
        ),
        _run_validator(
            "dependabot_coverage",
            [sys.executable, "scripts/ci/check_dependabot_coverage.py"],
        ),
    ]

    packet = _build_packet(
        resolved_sha,
        manifest_path,
        manifest,
        production_readiness_manifest_path,
        production_readiness_manifest,
        validators,
    )
    summary = _render_summary(packet)

    output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = output_dir / "release-evidence-packet.json"
    summary_path = output_dir / "release-evidence-summary.md"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(summary + "\n", encoding="utf-8")

    print(f"Wrote {_display_path(packet_path)}")
    print(f"Wrote {_display_path(summary_path)}")
    print(packet["overall_status"])
    return 0 if packet["overall_status"] == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--production-readiness-manifest",
        type=Path,
        default=DEFAULT_PRODUCTION_READINESS_MANIFEST,
        help="Validated manifest emitted by make production-readiness-gate.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--release-sha", type=str, default=None)
    parser.add_argument(
        "--allow-placeholder-sha",
        action="store_true",
        help="Allow REPLACE_WITH_COMMIT_SHA in checked-in example manifests.",
    )
    args = parser.parse_args(argv)

    manifest_path = args.manifest if args.manifest.is_absolute() else (ROOT / args.manifest)
    production_readiness_manifest_path = (
        args.production_readiness_manifest
        if args.production_readiness_manifest.is_absolute()
        else (ROOT / args.production_readiness_manifest)
    )
    output_dir = args.output_dir if args.output_dir.is_absolute() else (ROOT / args.output_dir)

    if not manifest_path.exists():
        print(f"manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        return generate_release_evidence_packet(
            manifest_path=manifest_path,
            production_readiness_manifest_path=production_readiness_manifest_path,
            output_dir=output_dir,
            release_sha=args.release_sha,
            allow_placeholder_sha=args.allow_placeholder_sha,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should fail with concise detail.
        print(f"failed to generate release evidence packet: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
