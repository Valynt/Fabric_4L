#!/usr/bin/env python3
"""Audit one service's frozen uv dependency graph and emit validated evidence."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

CLEAN_EXIT = 0
VULNERABLE_EXIT = 1
OPERATIONAL_ERROR_EXIT = 2
SCHEMA_VERSION = 1

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
ExecutableFinder = Callable[[str], str | None]


class AuditOperationalError(RuntimeError):
    """An audit could not produce trustworthy policy evidence."""


def _sanitize(value: str) -> str:
    value = re.sub(r"(?i)(token|password|secret|key)=([^\s&]+)", r"\1=[REDACTED]", value)
    return re.sub(r"(https?://)[^/@\s]+@", r"\1[REDACTED]@", value)


def _process_evidence(result: subprocess.CompletedProcess[str] | None) -> dict[str, str] | None:
    if result is None:
        return None
    return {"stdout": _sanitize(result.stdout or ""), "stderr": _sanitize(result.stderr or "")}


def _validate_report(report_path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not report_path.exists():
        raise AuditOperationalError("pip-audit did not produce a report")
    if report_path.stat().st_size == 0:
        raise AuditOperationalError("pip-audit produced an empty report")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditOperationalError(f"pip-audit report contains malformed JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise AuditOperationalError("pip-audit report root must be an object")
    dependencies = report.get("dependencies")
    if not isinstance(dependencies, list):
        raise AuditOperationalError("pip-audit report dependencies must be a list")

    findings: list[dict[str, object]] = []
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise AuditOperationalError(f"dependency entry {index} must be an object")
        name = dependency.get("name")
        if not isinstance(name, str) or not name.strip():
            raise AuditOperationalError(f"dependency entry {index} must have a non-empty package name")
        vulns = dependency.get("vulns")
        if not isinstance(vulns, list):
            raise AuditOperationalError(f"dependency {name} vulns must be a list")
        ids: list[str] = []
        details: list[dict[str, str]] = []
        for vuln_index, vulnerability in enumerate(vulns):
            if not isinstance(vulnerability, dict):
                raise AuditOperationalError(f"vulnerability {vuln_index} for {name} must be an object")
            canonical_id = vulnerability.get("id")
            if not isinstance(canonical_id, str) or not canonical_id.strip():
                raise AuditOperationalError(f"vulnerability {vuln_index} for {name} must have a non-empty canonical id")
            aliases = vulnerability.get("aliases", [])
            if not isinstance(aliases, list) or any(not isinstance(alias, str) or not alias for alias in aliases):
                raise AuditOperationalError(f"vulnerability {canonical_id} aliases must be a list of non-empty strings")
            ids.extend([canonical_id, *aliases])
            details.append({"id": canonical_id, "description": str(vulnerability.get("description", ""))})
        if ids:
            findings.append({"package": name, "ids": list(dict.fromkeys(ids)), "details": details})
    return report, findings


def _write_sarif(path: Path, dependency_source: Path, findings: list[dict[str, object]]) -> None:
    rules: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    seen_rules: set[str] = set()
    for finding in findings:
        for detail in finding["details"]:
            vuln_id = detail["id"]
            if vuln_id not in seen_rules:
                rules.append({
                    "id": vuln_id,
                    "name": vuln_id,
                    "shortDescription": {"text": detail["description"] or vuln_id},
                })
                seen_rules.add(vuln_id)
            results.append({
                "ruleId": vuln_id,
                "level": "error",
                "message": {"text": f"{vuln_id} affects {finding['package']}"},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": str(dependency_source)}}}],
            })
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "pip-audit", "rules": rules}}, "results": results}],
    }
    path.write_text(json.dumps(sarif, indent=2) + "\n", encoding="utf-8")


def run_scan(
    *,
    service_name: str,
    service_dir: Path,
    artifact_dir: Path,
    command_runner: CommandRunner = subprocess.run,
    executable_finder: ExecutableFinder = shutil.which,
) -> tuple[int, dict[str, object]]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    requirements_path = artifact_dir / "requirements.txt"
    report_path = artifact_dir / "report.json"
    sarif_path = artifact_dir / "report.sarif"
    diagnostic_path = artifact_dir / "diagnostic.json"
    lock_path = service_dir / "uv.lock"
    project_path = service_dir / "pyproject.toml"
    diagnostic: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "service": service_name,
        "outcome": "operational_error",
        "exit_code": OPERATIONAL_ERROR_EXIT,
        "dependency_source": str(lock_path),
        "requirements_file": str(requirements_path),
        "report_file": str(report_path),
        "sarif_file": str(sarif_path),
        "vulnerabilities": [],
        "error": None,
        "export": None,
        "scanner": None,
    }
    export_result: subprocess.CompletedProcess[str] | None = None
    scanner_result: subprocess.CompletedProcess[str] | None = None
    status = OPERATIONAL_ERROR_EXIT
    try:
        if not lock_path.is_file() or not project_path.is_file():
            raise AuditOperationalError(f"{service_dir} must contain both uv.lock and pyproject.toml")
        if executable_finder("uv") is None:
            raise AuditOperationalError("uv is unavailable")
        if executable_finder("pip-audit") is None:
            raise AuditOperationalError("pip-audit is unavailable")

        export_command = [
            "uv", "export", "--project", str(service_dir), "--locked", "--no-dev",
            "--no-emit-project", "--format", "requirements-txt", "--output-file", str(requirements_path),
        ]
        export_result = command_runner(export_command, text=True, capture_output=True, check=False)
        if export_result.returncode != 0:
            raise AuditOperationalError(f"frozen dependency export failed with exit code {export_result.returncode}")
        if not requirements_path.is_file() or requirements_path.stat().st_size == 0:
            raise AuditOperationalError("frozen dependency export did not produce a non-empty requirements file")

        scanner_command = [
            "pip-audit", "--requirement", str(requirements_path), "--format", "json",
            "--output", str(report_path), "--progress-spinner", "off",
            "--ignore-vuln", "PYSEC-2026-3552", "--ignore-vuln", "PYSEC-2026-3553", "--ignore-vuln", "PYSEC-2026-3554",
        ]
        scanner_result = command_runner(scanner_command, text=True, capture_output=True, check=False)
        if scanner_result.returncode not in (CLEAN_EXIT, VULNERABLE_EXIT):
            raise AuditOperationalError(f"pip-audit failed with unexpected exit code {scanner_result.returncode}")
        _, findings = _validate_report(report_path)
        if scanner_result.returncode == CLEAN_EXIT and findings:
            raise AuditOperationalError("pip-audit exit code 0 is inconsistent with reported vulnerabilities")
        if scanner_result.returncode == VULNERABLE_EXIT and not findings:
            raise AuditOperationalError("pip-audit exit code 1 is inconsistent with a report containing no vulnerabilities")

        _write_sarif(sarif_path, lock_path, findings)
        status = VULNERABLE_EXIT if findings else CLEAN_EXIT
        diagnostic["outcome"] = "vulnerable" if findings else "clean"
        diagnostic["exit_code"] = status
        diagnostic["vulnerabilities"] = [{"package": item["package"], "ids": item["ids"]} for item in findings]
    except (AuditOperationalError, OSError, subprocess.SubprocessError) as exc:
        diagnostic["error"] = str(exc)
    finally:
        diagnostic["export"] = _process_evidence(export_result)
        diagnostic["scanner"] = _process_evidence(scanner_result)
        try:
            diagnostic_path.write_text(json.dumps(diagnostic, indent=2) + "\n", encoding="utf-8")
        except OSError as write_exc:
            sys.stderr.write(f"Failed to write diagnostic to {diagnostic_path}: {write_exc}\n")
            try:
                sys.stderr.write(json.dumps(diagnostic, indent=2) + "\n")
            except TypeError:
                sys.stderr.write("Failed to serialize diagnostic for stderr output\n")
    return status, diagnostic


def _load_validated_diagnostic(diagnostic_path: Path, *, expected_status: int) -> tuple[int, dict[str, object] | None]:
    try:
        payload = json.loads(diagnostic_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise AuditOperationalError("diagnostic must be a JSON object")
        outcome = payload.get("outcome")
        saved_status = payload.get("exit_code")
        expected = {"clean": CLEAN_EXIT, "vulnerable": VULNERABLE_EXIT, "operational_error": OPERATIONAL_ERROR_EXIT}
        if outcome not in expected or saved_status != expected[outcome] or saved_status != expected_status:
            raise AuditOperationalError("saved audit status does not match the diagnostic outcome")
        required_fields = (
            "service",
            "dependency_source",
            "requirements_file",
            "report_file",
            "sarif_file",
            "vulnerabilities",
            "error",
        )
        if any(field not in payload for field in required_fields):
            raise AuditOperationalError("diagnostic is missing required schema fields")
        if outcome in {"clean", "vulnerable"}:
            for field in ("dependency_source", "requirements_file", "report_file", "sarif_file"):
                evidence_path = Path(payload[field])
                if not evidence_path.is_file() or evidence_path.stat().st_size == 0:
                    raise AuditOperationalError(f"required audit evidence is missing or empty: {field}")
            _, findings = _validate_report(Path(payload["report_file"]))
            if (outcome == "vulnerable") != bool(findings):
                raise AuditOperationalError("diagnostic outcome is inconsistent with the saved report")
    except (OSError, json.JSONDecodeError, AuditOperationalError) as exc:
        print(f"Dependency audit operational error: {exc}", file=sys.stderr)
        return OPERATIONAL_ERROR_EXIT, None
    return expected[outcome], payload


def _validate_vulnerability_entries(payload: dict[str, object]) -> list[tuple[str, str]] | None:
    vulnerabilities = payload.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        print("Dependency audit operational error: diagnostic vulnerabilities must be a list", file=sys.stderr)
        return None
    signatures: list[tuple[str, str]] = []
    for finding in vulnerabilities:
        if not isinstance(finding, dict):
            print(
                "Dependency audit operational error: diagnostic vulnerability entries must be objects",
                file=sys.stderr,
            )
            return None
        package = finding.get("package")
        ids = finding.get("ids")
        if (
            not isinstance(package, str)
            or not package.strip()
            or not isinstance(ids, list)
            or any(not isinstance(vuln_id, str) or not vuln_id for vuln_id in ids)
        ):
            print(
                "Dependency audit operational error: diagnostic vulnerability entry is malformed",
                file=sys.stderr,
            )
            return None
        signatures.extend((package, vuln_id) for vuln_id in ids)
    return signatures


def enforce(diagnostic_path: Path, *, expected_status: int) -> int:
    status, payload = _load_validated_diagnostic(diagnostic_path, expected_status=expected_status)
    if payload is None:
        return status
    outcome = payload.get("outcome")
    if outcome == "vulnerable":
        signatures = _validate_vulnerability_entries(payload)
        if signatures is None:
            return OPERATIONAL_ERROR_EXIT
        packages: dict[str, list[str]] = {}
        for package, vuln_id in signatures:
            packages.setdefault(package, []).append(vuln_id)
        for package, ids in packages.items():
            print(f"Vulnerable dependency: {package} ({', '.join(ids)})", file=sys.stderr)
    elif outcome == "operational_error":
        error = payload.get("error")
        print(
            f"Dependency audit operational error: {error if isinstance(error, str) else 'unknown'}",
            file=sys.stderr,
        )
    return status


def compare(
    current_diagnostic_path: Path,
    *,
    expected_current_status: int,
    baseline_diagnostic_path: Path,
    expected_baseline_status: int,
) -> int:
    current_status, current = _load_validated_diagnostic(
        current_diagnostic_path, expected_status=expected_current_status
    )
    if current is None or current_status == OPERATIONAL_ERROR_EXIT:
        return current_status
    baseline_status, baseline = _load_validated_diagnostic(
        baseline_diagnostic_path, expected_status=expected_baseline_status
    )
    if baseline is None or baseline_status == OPERATIONAL_ERROR_EXIT:
        return baseline_status
    if current_status == CLEAN_EXIT:
        return CLEAN_EXIT

    current_signatures = _validate_vulnerability_entries(current)
    baseline_signatures = _validate_vulnerability_entries(baseline)
    if current_signatures is None or baseline_signatures is None:
        return OPERATIONAL_ERROR_EXIT

    baseline_set = set(baseline_signatures)
    introduced = [signature for signature in current_signatures if signature not in baseline_set]
    inherited = [signature for signature in current_signatures if signature in baseline_set]
    for package, vuln_id in inherited:
        print(f"Inherited vulnerability: {package} ({vuln_id})")
    for package, vuln_id in introduced:
        print(f"Branch-introduced vulnerability: {package} ({vuln_id})", file=sys.stderr)
    return VULNERABLE_EXIT if introduced else CLEAN_EXIT


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan")
    scan.add_argument("--service-name", required=True)
    scan.add_argument("--service-dir", type=Path, required=True)
    scan.add_argument("--artifact-dir", type=Path, required=True)
    gate = subparsers.add_parser("enforce")
    gate.add_argument("--diagnostic", type=Path, required=True)
    gate.add_argument("--expected-status", type=int, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--current-diagnostic", type=Path, required=True)
    compare_parser.add_argument("--current-expected-status", type=int, required=True)
    compare_parser.add_argument("--baseline-diagnostic", type=Path, required=True)
    compare_parser.add_argument("--baseline-expected-status", type=int, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "scan":
        status, _ = run_scan(service_name=args.service_name, service_dir=args.service_dir, artifact_dir=args.artifact_dir)
        return status
    if args.command == "compare":
        return compare(
            args.current_diagnostic,
            expected_current_status=args.current_expected_status,
            baseline_diagnostic_path=args.baseline_diagnostic,
            expected_baseline_status=args.baseline_expected_status,
        )
    return enforce(args.diagnostic, expected_status=args.expected_status)


if __name__ == "__main__":
    raise SystemExit(main())
