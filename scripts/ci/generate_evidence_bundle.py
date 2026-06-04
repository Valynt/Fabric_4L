#!/usr/bin/env python3
"""Assemble a local audit/release evidence bundle.

The default mode is intentionally lightweight: it generates read-only summaries,
copies already-produced CI evidence when present, and records missing
environment-dependent artifacts as manifest gaps instead of running heavy gates.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "evidence"
GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
MAX_INCLUDED_FILE_BYTES = 20 * 1024 * 1024

HEAVY_EVIDENCE_EXPECTATIONS = (
    ("test summaries", "artifacts/**/*.xml"),
    ("security scan summaries", "artifacts/**/*security*"),
    ("contract drift reports", "artifacts/**/*contract*drift*"),
    ("container SBOM references", "artifacts/**/*sbom*"),
    ("K8s validation report", "artifacts/**/*k8s*"),
    ("observability dashboard/rule validation", "artifacts/**/*observability*"),
    ("release smoke results", "artifacts/release_smoke/**"),
)

SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "tests": (
        "artifacts/**/*.xml",
        "artifacts/**/*junit*",
        "artifacts/**/*test*report*.json",
        "artifacts/**/*pytest*.json",
        "artifacts/**/*playwright*.json",
    ),
    "security": (
        "artifacts/**/*.sarif",
        "artifacts/**/*bandit*",
        "artifacts/**/*security*",
        "artifacts/**/*trivy*",
        "artifacts/**/*zap*",
        "artifacts/**/*vulnerab*",
        "bandit-report.*",
        "security-tests.xml",
        "prompt-injection-tests.xml",
        "report_*.html",
        "report_*.json",
    ),
    "contracts": (
        "artifacts/contract-breaking/**",
        "artifacts/testing/*contract*",
        "artifacts/**/*contract*drift*",
        "artifacts/**/*openapi*",
    ),
    "migrations": (
        "artifacts/database/**",
        "artifacts/database-check-smoke/**",
        "artifacts/**/*migration*status*",
    ),
    "supply-chain": (
        "artifacts/**/*sbom*",
        "artifacts/**/*.spdx.json",
        "artifacts/**/*.cdx.json",
        "artifacts/**/*attestation*",
        "artifacts/**/*signing*",
        "sbom-*",
        "attestation-*",
        "signing-*",
    ),
    "k8s": (
        "artifacts/**/*k8s*",
        "artifacts/**/*kubernetes*",
        "artifacts/**/*manifest*validation*",
    ),
    "observability": (
        "artifacts/**/*observability*",
        "artifacts/**/*alert*",
        "artifacts/**/*grafana*",
        "artifacts/**/*prometheus*",
    ),
    "release-smoke": (
        "artifacts/release_smoke/**",
        "artifacts/**/*smoke-report*",
        "artifacts/**/*release_smoke*",
    ),
}


@dataclass(frozen=True)
class BundleFile:
    archive_path: str
    source_path: str
    size_bytes: int
    sha256: str


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _git_value(repo_root: Path, args: list[str], default: str = "unknown") -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else default


def _git_sha(repo_root: Path) -> str:
    for env_name in ("RELEASE_SHA", "GITHUB_SHA", "CI_COMMIT_SHA"):
        value = os.environ.get(env_name)
        if value:
            return value
    return _git_value(repo_root, ["rev-parse", "HEAD"])


def _short_sha(sha: str) -> str:
    return sha[:12] if sha and sha != "unknown" else "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_command(
    *,
    name: str,
    command: list[str],
    repo_root: Path,
    gaps: list[dict[str, Any]],
    staging_root: Path | None = None,
) -> dict[str, Any]:
    stdout = ""
    stderr = ""
    status = "pass"
    try:
        result = subprocess.run(command, cwd=repo_root, text=True, capture_output=True, check=False, timeout=180)
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + "\nTimed out after 180s\n"
        returncode = 124
        status = "timeout"
    except FileNotFoundError as exc:
        stderr = str(exc) + "\n"
        returncode = 127
        status = "missing-tool"

    if status == "pass" and returncode != 0:
        status = "finding" if returncode in {1, 2} else "fail"

    record = {
        "name": name,
        "command": command,
        "returncode": returncode,
        "status": status,
        "stdout_tail": stdout.strip()[-2000:],
        "stderr_tail": stderr.strip()[-2000:],
    }
    if staging_root is not None:
        output_dir = staging_root / "command-output" / name
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
        (output_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
        record["stdout_path"] = f"command-output/{name}/stdout.txt"
        record["stderr_path"] = f"command-output/{name}/stderr.txt"

    if returncode != 0:
        gaps.append(
            {
                "category": name,
                "severity": "warning",
                "reason": "summary_command_failed",
                "command": " ".join(command),
                "returncode": returncode,
                "status": status,
                "detail": (stderr.strip() or stdout.strip())[-500:],
            }
        )
    return record


def _safe_copy(source: Path, destination: Path, *, repo_root: Path, gaps: list[dict[str, Any]]) -> bool:
    if not source.is_file():
        return False
    resolved_repo = repo_root.resolve()
    resolved_source = source.resolve(strict=False)
    try:
        resolved_source.relative_to(resolved_repo)
    except ValueError:
        gaps.append(
            {
                "category": "file-copy",
                "severity": "warning",
                "reason": "source_outside_repo",
                "source_path": source.as_posix(),
            }
        )
        return False
    size = source.stat().st_size
    if size > MAX_INCLUDED_FILE_BYTES:
        gaps.append(
            {
                "category": "file-size",
                "severity": "info",
                "reason": "file_too_large",
                "source_path": _display_path(source, repo_root),
                "size_bytes": size,
                "limit_bytes": MAX_INCLUDED_FILE_BYTES,
            }
        )
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def _iter_candidate_files(repo_root: Path, patterns: Iterable[str]) -> list[Path]:
    matches: dict[str, Path] = {}
    evidence_root = (repo_root / "artifacts" / "evidence").resolve()
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            try:
                path.resolve().relative_to(evidence_root)
                continue
            except ValueError:
                pass
            matches.setdefault(path.resolve().as_posix(), path)
    return [matches[key] for key in sorted(matches)]


def _copy_section_artifacts(
    *,
    section: str,
    patterns: Iterable[str],
    repo_root: Path,
    staging_root: Path,
    gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    copied = 0
    for source in _iter_candidate_files(repo_root, patterns):
        relative = _display_path(source, repo_root)
        destination = staging_root / section / relative
        if _safe_copy(source, destination, repo_root=repo_root, gaps=gaps):
            copied += 1
    return {"section": section, "patterns": list(patterns), "files_copied": copied}


def _generate_launch_scorecard(repo_root: Path, staging_root: Path, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/ci/generate_launch_evidence_bundle.py",
        "--dry-run",
        "--artifacts-only",
        "--up-to-stage",
        "evidence_archive",
        "--repo-root",
        str(repo_root),
    ]
    result = subprocess.run(command, cwd=repo_root, text=True, capture_output=True, check=False)
    record = {
        "name": "launch_readiness_scorecard",
        "command": command,
        "returncode": result.returncode,
    }
    if result.returncode == 0:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            gaps.append(
                {
                    "category": "launch-readiness",
                    "severity": "warning",
                    "reason": "invalid_scorecard_json",
                    "detail": str(exc),
                }
            )
        else:
            _write_json(staging_root / "maturity" / "launch-readiness-scorecard.json", payload)
            record["output"] = "maturity/launch-readiness-scorecard.json"
            return record
    gaps.append(
        {
            "category": "launch-readiness",
            "severity": "warning",
            "reason": "scorecard_generation_failed",
            "returncode": result.returncode,
            "detail": (result.stderr.strip() or result.stdout.strip())[-500:],
        }
    )
    record["stderr_tail"] = result.stderr.strip()[-1000:]
    record["stdout_tail"] = result.stdout.strip()[-1000:]
    return record


def _generate_release_packet(repo_root: Path, staging_root: Path, release_sha: str, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    output_dir = staging_root / "maturity" / "release-evidence-packet"
    command = [
        sys.executable,
        "scripts/ci/generate_release_evidence_packet.py",
        "--output-dir",
        str(output_dir),
        "--release-sha",
        release_sha,
        "--allow-placeholder-sha",
    ]
    record = _run_command(
        name="release_evidence_packet",
        command=command,
        repo_root=repo_root,
        gaps=gaps,
        staging_root=staging_root,
    )
    if output_dir.exists():
        record["output"] = "maturity/release-evidence-packet"
    return record


def _write_openapi_inventory(repo_root: Path, staging_root: Path) -> dict[str, Any]:
    specs = []
    for path in sorted((repo_root / "contracts" / "openapi").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        raw = path.read_bytes()
        specs.append(
            {
                "path": _display_path(path, repo_root),
                "title": payload.get("info", {}).get("title") if isinstance(payload, dict) else None,
                "version": payload.get("info", {}).get("version") if isinstance(payload, dict) else None,
                "paths": len(payload.get("paths", {})) if isinstance(payload, dict) else 0,
                "schemas": len(payload.get("components", {}).get("schemas", {})) if isinstance(payload, dict) else 0,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    report = {
        "generated_at_utc": _utc_now(),
        "report_type": "openapi-breaking-change-inventory",
        "baseline_note": (
            "Local evidence records current OpenAPI checksums and command output. "
            "Release-candidate CI should compare this inventory to the prior release baseline."
        ),
        "specs": specs,
    }
    _write_json(staging_root / "contracts" / "openapi-breaking-change-report.json", report)
    return {"name": "openapi_inventory", "output": "contracts/openapi-breaking-change-report.json", "spec_count": len(specs)}


def _generate_contract_reports(repo_root: Path, gaps: list[dict[str, Any]], staging_root: Path | None = None) -> dict[str, Any]:
    command = [sys.executable, "scripts/ci/openapi_breaking_change_gate.py"]
    return _run_command(
        name="openapi_breaking_change_report",
        command=command,
        repo_root=repo_root,
        gaps=gaps,
        staging_root=staging_root,
    )


def _generate_migration_status(repo_root: Path, gaps: list[dict[str, Any]], staging_root: Path | None = None) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/ci/migration_status_report.py",
        "--mode",
        "status",
        "--allow-database-unavailable",
    ]
    return _run_command(
        name="migration_status",
        command=command,
        repo_root=repo_root,
        gaps=gaps,
        staging_root=staging_root,
    )


def _write_migration_inventory(repo_root: Path, staging_root: Path) -> dict[str, Any]:
    managed = []
    for path in sorted(repo_root.glob("services/*/migrations/alembic.ini")):
        managed.append({"service": path.parts[-3], "alembic_ini": _display_path(path, repo_root)})
    for path in sorted(repo_root.glob("services/*/alembic.ini")):
        managed.append({"service": path.parts[-2], "alembic_ini": _display_path(path, repo_root)})
    payload = {"generated_at_utc": _utc_now(), "managed_services": managed}
    _write_json(staging_root / "migrations" / "migration-status.json", payload)
    return {"name": "migration_inventory", "output": "migrations/migration-status.json", "service_count": len(managed)}


def _workflow_event_names(on_value: Any) -> list[str]:
    if isinstance(on_value, str):
        return [on_value]
    if isinstance(on_value, list):
        return [str(item) for item in on_value]
    if isinstance(on_value, dict):
        return sorted(str(key) for key in on_value)
    return []


def _load_workflow(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None  # type: ignore

    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text) or {}
        if isinstance(loaded, dict):
            on_value = loaded.get("on")
            if on_value is None and True in loaded:
                on_value = loaded[True]
            jobs = loaded.get("jobs") if isinstance(loaded.get("jobs"), dict) else {}
            return {
                "name": loaded.get("name") or path.stem,
                "events": _workflow_event_names(on_value),
                "jobs": sorted(str(key) for key in jobs),
                "parser": "pyyaml",
            }

    jobs = []
    for line in text.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            key = line.strip()[:-1]
            if key not in {"on", "jobs", "permissions", "env"}:
                jobs.append(key)
    return {"name": path.stem, "events": [], "jobs": sorted(jobs), "parser": "fallback"}


def _generate_workflow_registry(repo_root: Path, staging_root: Path) -> dict[str, Any]:
    workflows = []
    for path in sorted((repo_root / ".github" / "workflows").glob("*.yml")):
        entry = _load_workflow(path)
        entry["path"] = _display_path(path, repo_root)
        workflows.append(entry)
    for path in sorted((repo_root / ".github" / "workflows").glob("*.yaml")):
        entry = _load_workflow(path)
        entry["path"] = _display_path(path, repo_root)
        workflows.append(entry)

    payload = {
        "generated_at_utc": _utc_now(),
        "workflow_count": len(workflows),
        "workflows": workflows,
    }
    _write_json(staging_root / "ci" / "workflow-registry.json", payload)
    return {"name": "workflow_registry", "output": "ci/workflow-registry.json", "workflow_count": len(workflows)}


def _generate_observability_inventory(repo_root: Path, staging_root: Path, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    dashboards = []
    dashboard_root = repo_root / "monitoring" / "grafana" / "dashboards"
    for path in sorted(dashboard_root.glob("*.json")):
        status = "valid"
        title = path.stem
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                title = str(payload.get("title") or title)
        except Exception as exc:  # noqa: BLE001 - inventory should not abort bundling.
            status = "invalid"
            gaps.append(
                {
                    "category": "observability",
                    "severity": "warning",
                    "reason": "invalid_grafana_dashboard_json",
                    "source_path": _display_path(path, repo_root),
                    "detail": str(exc),
                }
            )
        dashboards.append({"path": _display_path(path, repo_root), "title": title, "status": status})

    rule_files = [
        path
        for root in (repo_root / "monitoring", repo_root / "k8s" / "monitoring")
        if root.exists()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".yml", ".yaml", ".json"}
    ]
    payload = {
        "generated_at_utc": _utc_now(),
        "grafana_dashboards": dashboards,
        "grafana_dashboard_count": len(dashboards),
        "rule_files": [_display_path(path, repo_root) for path in rule_files],
        "rule_file_count": len(rule_files),
    }
    _write_json(staging_root / "observability" / "observability-inventory.json", payload)
    return {
        "name": "observability_inventory",
        "output": "observability/observability-inventory.json",
        "grafana_dashboard_count": len(dashboards),
        "rule_file_count": len(rule_files),
    }


def _generate_k8s_inventory(repo_root: Path, staging_root: Path, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    k8s_root = repo_root / "k8s"
    files = []
    if k8s_root.exists():
        files = [
            path
            for path in sorted(k8s_root.rglob("*"))
            if path.is_file() and path.suffix.lower() in {".yml", ".yaml", ".json"}
        ]
    validation_artifacts = _iter_candidate_files(
        repo_root,
        ("artifacts/**/*k8s*", "artifacts/**/*kubernetes*", "artifacts/**/*manifest*validation*"),
    )
    if not validation_artifacts:
        gaps.append(
            {
                "category": "k8s",
                "severity": "info",
                "reason": "validation_artifact_missing",
                "expected": "K8s validation report from CI or local validation",
            }
        )
    payload = {
        "generated_at_utc": _utc_now(),
        "manifest_count": len(files),
        "manifest_paths": [_display_path(path, repo_root) for path in files],
        "validation_artifacts": [_display_path(path, repo_root) for path in validation_artifacts],
    }
    _write_json(staging_root / "k8s" / "k8s-validation-summary.json", payload)
    return {
        "name": "k8s_inventory",
        "output": "k8s/k8s-validation-summary.json",
        "manifest_count": len(files),
        "validation_artifact_count": len(validation_artifacts),
    }


def _write_test_summary(staging_root: Path, section_sources: list[dict[str, Any]]) -> dict[str, Any]:
    copied = sum(source.get("files_copied", 0) for source in section_sources if source.get("section") == "tests")
    payload = {
        "generated_at_utc": _utc_now(),
        "referenced_test_artifact_count": copied,
        "note": "The bundle copies existing JUnit, pytest, Playwright, and test report artifacts when present.",
    }
    _write_json(staging_root / "tests" / "test-summaries.json", payload)
    return {"name": "test_summary", "output": "tests/test-summaries.json", "artifact_count": copied}


def _write_security_summary(staging_root: Path, section_sources: list[dict[str, Any]]) -> dict[str, Any]:
    security_count = sum(source.get("files_copied", 0) for source in section_sources if source.get("section") == "security")
    sbom_count = sum(source.get("files_copied", 0) for source in section_sources if source.get("section") == "supply-chain")
    payload = {
        "generated_at_utc": _utc_now(),
        "referenced_security_artifact_count": security_count,
        "referenced_sbom_artifact_count": sbom_count,
        "note": "Security scans and SBOMs are copied from existing CI/local artifacts; the generator does not build images or run container scans.",
    }
    _write_json(staging_root / "security" / "security-scan-summaries.json", payload)
    _write_json(staging_root / "supply-chain" / "container-sbom-references.json", payload)
    return {"name": "security_summary", "output": "security/security-scan-summaries.json", "security_count": security_count, "sbom_count": sbom_count}


def _write_release_smoke_summary(staging_root: Path, section_sources: list[dict[str, Any]]) -> dict[str, Any]:
    copied = sum(source.get("files_copied", 0) for source in section_sources if source.get("section") == "release-smoke")
    payload = {
        "generated_at_utc": _utc_now(),
        "command": "make test-backend-integrated-release-smoke",
        "artifact_count": copied,
        "note": (
            "The evidence bundle records existing release-smoke artifacts when present. "
            "Run make test-backend-integrated-release-smoke before pnpm evidence:bundle to include fresh live L1-L6 smoke results."
        ),
    }
    _write_json(staging_root / "release-smoke" / "release-smoke-results.json", payload)
    return {"name": "release_smoke_summary", "output": "release-smoke/release-smoke-results.json", "artifact_count": copied}


def _write_readme(staging_root: Path, bundle_name: str) -> None:
    content = f"""# Value Fabric Evidence Bundle

Bundle: `{bundle_name}`

This archive consolidates repository-owned release and audit evidence for
reviewers. It is generated by `pnpm evidence:bundle` and intentionally avoids
running Docker release smoke, live scans, full test suites, or image builds.

## How to Review

1. Open `manifest.json`.
2. Confirm `git_sha` matches the release candidate under review.
3. Verify each archived file checksum by recomputing SHA-256 over the listed
   path and comparing it with `manifest.files[*].sha256`.
4. Review `manifest.evidence_gaps` before treating the bundle as production
   release evidence. Gaps mark missing live or heavyweight CI evidence that was
   not present when the bundle was assembled.

## Main Sections

- `maturity/`: release evidence packet and launch readiness scorecard.
- `tests/`: copied JUnit, pytest, Playwright, and test summary artifacts.
- `security/`: copied SAST, security regression, vulnerability, and scan files.
- `contracts/`: OpenAPI breaking-change and contract drift reports.
- `migrations/`: migration status artifacts.
- `supply-chain/`: SBOM, signing, and attestation references.
- `k8s/`: Kubernetes inventory and validation evidence.
- `observability/`: dashboard and alert/rule inventory.
- `ci/`: workflow registry.
- `release-smoke/`: release smoke outputs when present.
"""
    (staging_root / "README.md").write_text(content, encoding="utf-8")


def _collect_manifest_files(staging_root: Path, repo_root: Path) -> list[BundleFile]:
    files: list[BundleFile] = []
    paths = sorted(
        (p for p in staging_root.rglob("*") if p.is_file()),
        key=lambda candidate: candidate.relative_to(staging_root).as_posix(),
    )
    for path in paths:
        archive_path = path.relative_to(staging_root).as_posix()
        if archive_path == "manifest.json":
            continue
        files.append(
            BundleFile(
                archive_path=archive_path,
                source_path=_display_path(path, repo_root),
                size_bytes=path.stat().st_size,
                sha256=_sha256(path),
            )
        )
    return files


def _write_manifest(
    *,
    staging_root: Path,
    repo_root: Path,
    bundle_id: str,
    bundle_name: str,
    release_sha: str,
    input_sources: list[dict[str, Any]],
    evidence_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    files = _collect_manifest_files(staging_root, repo_root)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator": "scripts/ci/generate_evidence_bundle.py",
        "generator_version": GENERATOR_VERSION,
        "generated_at_utc": _utc_now(),
        "git_sha": release_sha,
        "git_branch": _git_value(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "bundle_id": bundle_id,
        "bundle_name": bundle_name,
        "bundle_contents": [
            "maturity scorecard",
            "test summaries",
            "security scan summaries",
            "contract drift reports",
            "OpenAPI breaking-change report",
            "migration status",
            "container SBOM references",
            "K8s validation report",
            "observability dashboard/rule validation",
            "CI workflow registry",
            "release smoke results",
        ],
        "input_sources": input_sources,
        "evidence_gaps": evidence_gaps,
        "manifest_integrity": {
            "archive_path": "manifest.json",
            "note": "manifest.json is excluded from its own file checksum list; verify it through the archive checksum.",
        },
        "files": [file.__dict__ for file in files],
    }
    _write_json(staging_root / "manifest.json", manifest)
    return manifest


def _reset_tarinfo(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    tarinfo.uid = 0
    tarinfo.gid = 0
    tarinfo.uname = ""
    tarinfo.gname = ""
    tarinfo.mtime = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
    return tarinfo


def _create_archive(staging_root: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                paths = sorted(
                    (p for p in staging_root.rglob("*") if p.is_file()),
                    key=lambda candidate: candidate.relative_to(staging_root).as_posix(),
                )
                for path in paths:
                    tar.add(path, arcname=path.relative_to(staging_root).as_posix(), filter=_reset_tarinfo)


def generate_evidence_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    release_sha: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_sha = release_sha or _git_sha(repo_root)
    bundle_id = f"value-fabric-evidence-{_short_sha(resolved_sha)}"
    bundle_name = f"{bundle_id}.tar.gz"
    archive_path = output_dir / bundle_name
    gaps: list[dict[str, Any]] = []
    input_sources: list[dict[str, Any]] = []

    for stale_archive in sorted(output_dir.glob("*.tar.gz")):
        if stale_archive != archive_path:
            stale_archive.unlink()

    with tempfile.TemporaryDirectory(prefix="evidence-bundle-", dir=output_dir) as temp_dir:
        staging_root = Path(temp_dir) / bundle_id
        staging_root.mkdir(parents=True, exist_ok=True)

        input_sources.append(_generate_launch_scorecard(repo_root, staging_root, gaps))
        input_sources.append(_generate_release_packet(repo_root, staging_root, resolved_sha, gaps))
        input_sources.append(_write_openapi_inventory(repo_root, staging_root))
        input_sources.append(_generate_contract_reports(repo_root, gaps, staging_root))
        input_sources.append(_write_migration_inventory(repo_root, staging_root))
        input_sources.append(_generate_migration_status(repo_root, gaps, staging_root))
        input_sources.append(_generate_workflow_registry(repo_root, staging_root))
        input_sources.append(_generate_observability_inventory(repo_root, staging_root, gaps))
        input_sources.append(_generate_k8s_inventory(repo_root, staging_root, gaps))

        section_sources = []
        for section, patterns in SECTION_PATTERNS.items():
            section_source = _copy_section_artifacts(
                section=section,
                patterns=patterns,
                repo_root=repo_root,
                staging_root=staging_root,
                gaps=gaps,
            )
            section_sources.append(section_source)
            input_sources.append(section_source)

        input_sources.append(_write_test_summary(staging_root, section_sources))
        input_sources.append(_write_security_summary(staging_root, section_sources))
        input_sources.append(_write_release_smoke_summary(staging_root, section_sources))

        for label, pattern in HEAVY_EVIDENCE_EXPECTATIONS:
            if not _iter_candidate_files(repo_root, (pattern,)):
                gaps.append(
                    {
                        "category": label,
                        "severity": "info",
                        "reason": "optional_heavy_evidence_missing",
                        "expected_pattern": pattern,
                    }
                )

        _write_readme(staging_root, bundle_name)
        manifest = _write_manifest(
            staging_root=staging_root,
            repo_root=repo_root,
            bundle_id=bundle_id,
            bundle_name=bundle_name,
            release_sha=resolved_sha,
            input_sources=input_sources,
            evidence_gaps=gaps,
        )
        _create_archive(staging_root, archive_path)

    summary = {
        "archive_path": _display_path(archive_path, repo_root),
        "archive_sha256": _sha256(archive_path),
        "bundle_id": bundle_id,
        "file_count": len(manifest["files"]),
        "evidence_gap_count": len(gaps),
    }
    _write_json(output_dir / f"{bundle_id}.summary.json", summary)
    (output_dir / "LATEST").write_text(bundle_name + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", "--output-root", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--release-sha", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = generate_evidence_bundle(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        release_sha=args.release_sha,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
