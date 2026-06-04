#!/usr/bin/env python3
<<<<<<< ours
"""Assemble a local audit/release evidence bundle.

The default mode is intentionally lightweight: it generates read-only summaries,
copies already-produced CI evidence when present, and records missing
environment-dependent artifacts as manifest gaps instead of running heavy gates.
=======
"""Generate a consolidated audit/release evidence bundle.

The bundle intentionally combines freshly generated local command output with
references to heavyweight CI artifacts (container scans, SBOM attestations, live
release smoke evidence) so auditors can review one immutable tarball while the
same command remains runnable on developer workstations.
>>>>>>> theirs
"""

from __future__ import annotations

import argparse
<<<<<<< ours
import gzip
=======
>>>>>>> theirs
import hashlib
import json
import os
import shutil
import subprocess
<<<<<<< ours
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
    ("container SBOM references", "artifacts/**/*sbom*"),
    ("K8s validation report", "artifacts/**/*k8s*"),
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


def _git_sha(repo_root: Path) -> str:
    for env_name in ("RELEASE_SHA", "GITHUB_SHA", "CI_COMMIT_SHA"):
        value = os.environ.get(env_name)
        if value:
            return value
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "unknown"


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
) -> dict[str, Any]:
    result = subprocess.run(command, cwd=repo_root, text=True, capture_output=True, check=False)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    record = {
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
    }
    if result.returncode != 0:
        gaps.append(
            {
                "category": name,
                "severity": "warning",
                "reason": "summary_command_failed",
                "command": " ".join(command),
                "returncode": result.returncode,
                "detail": (stderr or stdout)[-500:],
            }
        )
    return record


def _safe_copy(source: Path, destination: Path, *, repo_root: Path, gaps: list[dict[str, Any]]) -> bool:
    if not source.is_file():
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
    record = _run_command(name="release_evidence_packet", command=command, repo_root=repo_root, gaps=gaps)
    if output_dir.exists():
        record["output"] = "maturity/release-evidence-packet"
    return record


def _generate_contract_reports(repo_root: Path, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [sys.executable, "scripts/ci/openapi_breaking_change_gate.py"]
    return _run_command(name="openapi_breaking_change_report", command=command, repo_root=repo_root, gaps=gaps)


def _generate_migration_status(repo_root: Path, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/ci/migration_status_report.py",
        "--mode",
        "status",
        "--allow-database-unavailable",
    ]
    return _run_command(name="migration_status", command=command, repo_root=repo_root, gaps=gaps)


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

    # Fallback is intentionally simple; it still gives auditors a registry.
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
=======
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts" / "evidence"
DEFAULT_WORK_ROOT = ROOT / "artifacts" / "evidence" / "work"

EVIDENCE_COMMANDS: tuple[tuple[str, str, list[str]], ...] = (
    (
        "maturity-scorecard",
        "Maturity scorecard / contract compliance posture",
        [
            "python",
            "scripts/ci/contract_scorecard.py",
            "--output",
            "{bundle}/maturity/contract-scorecard.json",
        ],
    ),
    (
        "contract-drift",
        "Contract drift and compliance gate",
        ["python", "scripts/ci/platform_contract_lint.py"],
    ),
    (
        "openapi-drift",
        "OpenAPI endpoint-family and breaking-change guard coverage",
        ["python", "scripts/ci/check_contract_endpoint_family_coverage.py"],
    ),
    (
        "migration-status",
        "Alembic migration entrypoint/head status",
        ["python", "scripts/ci/check_migration_entrypoints.py"],
    ),
    (
        "security-config",
        "Security configuration and bypass policy",
        ["python", "scripts/ci/check_config_policy.py"],
    ),
    (
        "k8s-validation",
        "Kubernetes manifest consistency validation",
        ["python", "scripts/ci/check_k8s_manifest_consistency.py"],
    ),
    (
        "observability-validation",
        "Observability alert/dashboard production metadata validation",
        ["python", "scripts/ci/check_production_alert_metadata.py"],
    ),
    (
        "ci-workflow-registry",
        "CI workflow target and artifact registry validation",
        ["python", "scripts/ci/check_workflow_targets_and_artifacts.py"],
    ),
)

REFERENCE_GLOBS: dict[str, tuple[str, ...]] = {
    "test-summaries": (
        "artifacts/**/pytest*.xml",
        "artifacts/**/*junit*.xml",
        "artifacts/**/test*.json",
        "reports/**/*test*.json",
    ),
    "security-scan-summaries": (
        "artifacts/**/trivy*",
        "artifacts/**/bandit*",
        "artifacts/**/zap*",
        "artifacts/**/security*.xml",
        "reports/**/*security*",
    ),
    "contract-drift-reports": (
        "artifacts/**/*contract*",
        "reports/**/*contract*",
    ),
    "container-sbom-references": (
        "artifacts/**/sbom*.json",
        "artifacts/**/*.cdx.json",
        "artifacts/**/*.spdx.json",
    ),
    "k8s-validation": ("artifacts/k8s-validation/**/*",),
    "observability-validation": (
        "artifacts/**/*observability*",
        "artifacts/**/*alert*",
        "reports/**/*observability*",
    ),
    "release-smoke-results": (
        "artifacts/release_smoke/**/*",
        "artifacts/**/*release*smoke*",
    ),
}

WORKFLOW_HINTS: dict[str, tuple[str, ...]] = {
    "tests": ("test", "pytest", "vitest", "playwright"),
    "security": ("security", "trivy", "bandit", "zap", "codeql", "supply-chain"),
    "contracts": ("contract", "openapi", "api"),
    "migrations": ("migration", "database", "alembic"),
    "k8s": ("k8s", "kubernetes", "deploy"),
    "observability": ("observability", "alert", "slo", "monitoring"),
    "release": ("release", "smoke", "readiness", "evidence"),
}


@dataclass(frozen=True)
class CommandResult:
    key: str
    description: str
    command: list[str]
    exit_code: int
    stdout_path: str
    stderr_path: str
    status: str


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_value(args: list[str], default: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return default


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def safe_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
        target = src.resolve(strict=False)
        if not str(target).startswith(str(ROOT)):
            return
    shutil.copy2(src, dest)


def classify_status(exit_code: int) -> str:
    # Evidence generation should be reproducible even when a gate records a
    # release-readiness finding. The manifest preserves the raw exit code while
    # distinguishing collected findings from generator/runtime failures.
    if exit_code == 0:
        return "pass"
    if exit_code in {1, 2}:
        return "finding"
    return "fail"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_command(
    key: str, description: str, command: list[str], bundle_dir: Path, timeout: int
) -> CommandResult:
    rendered = [part.replace("{bundle}", str(bundle_dir)) for part in command]
    output_dir = bundle_dir / "command-output" / key
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"
    try:
        proc = subprocess.run(
            rendered,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")
        exit_code = proc.returncode
        status = classify_status(proc.returncode)
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(
            (exc.stderr or "") + f"\nTimed out after {timeout}s\n", encoding="utf-8"
        )
        exit_code = 124
        status = "timeout"
    except FileNotFoundError as exc:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc) + "\n", encoding="utf-8")
        exit_code = 127
        status = "missing-tool"
    return CommandResult(
        key,
        description,
        rendered,
        exit_code,
        display_path(stdout_path),
        display_path(stderr_path),
        status,
    )


def collect_reference_artifacts(bundle_dir: Path) -> dict[str, list[dict[str, str]]]:
    collected: dict[str, list[dict[str, str]]] = {}
    bundle_resolved = bundle_dir.resolve()
    for category, patterns in REFERENCE_GLOBS.items():
        items: list[dict[str, str]] = []
        seen: set[Path] = set()
        for pattern in patterns:
            for src in sorted(ROOT.glob(pattern)):
                if not src.is_file() or src in seen:
                    continue
                if bundle_resolved in src.resolve().parents:
                    continue
                seen.add(src)
                rel = src.relative_to(ROOT)
                dest = bundle_dir / "referenced-artifacts" / category / rel
                safe_copy(src, dest)
                items.append({"source": str(rel), "bundled_as": display_path(dest)})
        collected[category] = items
    return collected


def summarize_openapi(bundle_dir: Path) -> dict[str, Any]:
    specs = []
    for path in sorted((ROOT / "contracts" / "openapi").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = path.read_bytes()
        specs.append(
            {
                "path": display_path(path),
                "title": data.get("info", {}).get("title"),
                "version": data.get("info", {}).get("version"),
                "paths": len(data.get("paths", {})),
                "schemas": len(data.get("components", {}).get("schemas", {})),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    report = {
        "generated_at": utc_now(),
        "report_type": "openapi-breaking-change-inventory",
        "baseline_note": (
            "This local bundle records current OpenAPI contract checksums and command output from "
            "scripts/ci/check_contract_freshness.sh. CI release-candidate runs should compare this "
            "inventory to the previous release baseline before approving breaking API changes."
        ),
        "specs": specs,
    }
    write_json(bundle_dir / "openapi" / "breaking-change-report.json", report)
    return report


def workflow_registry(bundle_dir: Path) -> dict[str, Any]:
    workflows = []
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")) + sorted(
        (ROOT / ".github" / "workflows").glob("*.yaml")
    ):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        categories = sorted(
            category
            for category, hints in WORKFLOW_HINTS.items()
            if any(hint in text or hint in path.name for hint in hints)
        )
        workflows.append({"path": display_path(path), "categories": categories})
    registry = {
        "generated_at": utc_now(),
        "workflow_count": len(workflows),
        "workflows": workflows,
    }
    write_json(bundle_dir / "ci" / "workflow-registry.json", registry)
    return registry


def test_summary(
    bundle_dir: Path, referenced: dict[str, list[dict[str, str]]]
) -> dict[str, Any]:
    tests = referenced.get("test-summaries", [])
    payload = {
        "generated_at": utc_now(),
        "summary": {
            "referenced_test_artifact_count": len(tests),
            "pytest_targets_documented": (
                "pytest.ini" if (ROOT / "pytest.ini").exists() else None
            ),
            "frontend_test_package": (
                "apps/web/package.json"
                if (ROOT / "apps/web/package.json").exists()
                else None
            ),
        },
        "artifacts": tests,
    }
    write_json(bundle_dir / "tests" / "test-summaries.json", payload)
    return payload


def security_summary(
    bundle_dir: Path, referenced: dict[str, list[dict[str, str]]]
) -> dict[str, Any]:
    payload = {
        "generated_at": utc_now(),
        "referenced_security_artifact_count": len(
            referenced.get("security-scan-summaries", [])
        ),
        "referenced_sbom_artifact_count": len(
            referenced.get("container-sbom-references", [])
        ),
        "security_workflows": [
            display_path(p)
            for p in sorted((ROOT / ".github" / "workflows").glob("*security*.yml"))
        ],
        "supply_chain_workflows": [
            display_path(p)
            for p in sorted((ROOT / ".github" / "workflows").glob("*supply*.yml"))
        ],
        "artifacts": {
            "security_scan_summaries": referenced.get("security-scan-summaries", []),
            "container_sbom_references": referenced.get(
                "container-sbom-references", []
            ),
        },
    }
    write_json(bundle_dir / "security" / "security-scan-summaries.json", payload)
    return payload


def migration_status(bundle_dir: Path) -> dict[str, Any]:
    managed = []
    for path in sorted(ROOT.glob("services/*/migrations/alembic.ini")):
        managed.append({"service": path.parts[-3], "alembic_ini": display_path(path)})
    for path in sorted(ROOT.glob("services/*/alembic.ini")):
        managed.append({"service": path.parts[-2], "alembic_ini": display_path(path)})
    payload = {"generated_at": utc_now(), "managed_services": managed}
    write_json(bundle_dir / "migrations" / "migration-status.json", payload)
    return payload


def release_smoke_summary(
    bundle_dir: Path, referenced: dict[str, list[dict[str, str]]]
) -> dict[str, Any]:
    artifacts = referenced.get("release-smoke-results", [])
    payload = {
        "generated_at": utc_now(),
        "command": "make test-backend-integrated-release-smoke",
        "underlying_script": "scripts/ci/run_release_smoke.sh",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "local_note": (
            "The evidence bundle records existing release-smoke artifacts when present. "
            "Run make test-backend-integrated-release-smoke before pnpm evidence:bundle to include fresh live L1-L6 smoke results."
        ),
    }
    write_json(bundle_dir / "release" / "release-smoke-results.json", payload)
    return payload


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_files(bundle_dir: Path) -> list[dict[str, Any]]:
    files = []
    for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
        if path.name == "manifest.json":
            continue
        files.append(
            {
                "path": str(path.relative_to(bundle_dir)),
                "size_bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
>>>>>>> theirs
        )
    return files


<<<<<<< ours
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
        "bundle_id": bundle_id,
        "bundle_name": bundle_name,
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
    tarinfo.mtime = 0
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

    with tempfile.TemporaryDirectory(prefix="evidence-bundle-", dir=output_dir) as temp_dir:
        staging_root = Path(temp_dir) / bundle_id
        staging_root.mkdir(parents=True, exist_ok=True)

        input_sources.append(_generate_launch_scorecard(repo_root, staging_root, gaps))
        input_sources.append(_generate_release_packet(repo_root, staging_root, resolved_sha, gaps))
        input_sources.append(_generate_contract_reports(repo_root, gaps))
        input_sources.append(_generate_migration_status(repo_root, gaps))
        input_sources.append(_generate_workflow_registry(repo_root, staging_root))
        input_sources.append(_generate_observability_inventory(repo_root, staging_root, gaps))
        input_sources.append(_generate_k8s_inventory(repo_root, staging_root, gaps))

        for section, patterns in SECTION_PATTERNS.items():
            input_sources.append(
                _copy_section_artifacts(
                    section=section,
                    patterns=patterns,
                    repo_root=repo_root,
                    staging_root=staging_root,
                    gaps=gaps,
                )
            )

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
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
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
=======
def create_tarball(bundle_dir: Path, tar_path: Path) -> None:
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "w:gz") as tar:
        for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
            arcname = Path("evidence-bundle") / path.relative_to(bundle_dir)
            info = tar.gettarinfo(str(path), arcname=str(arcname))
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
            with path.open("rb") as handle:
                tar.addfile(info, handle)


def build_bundle(output_root: Path, work_root: Path, timeout: int) -> Path:
    sha = git_value(["rev-parse", "--short=12", "HEAD"], "unknown")
    timestamp = utc_now().replace(":", "").replace("-", "")
    bundle_dir = work_root / f"evidence-bundle-{sha}-{timestamp}"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)
    for category in (
        "maturity",
        "tests",
        "security",
        "openapi",
        "migrations",
        "release",
        "ci",
    ):
        (bundle_dir / category).mkdir(parents=True, exist_ok=True)

    command_results = [
        run_command(key, description, command, bundle_dir, timeout)
        for key, description, command in EVIDENCE_COMMANDS
    ]
    referenced = collect_reference_artifacts(bundle_dir)
    summaries = {
        "openapi_breaking_change_report": summarize_openapi(bundle_dir),
        "ci_workflow_registry": workflow_registry(bundle_dir),
        "test_summaries": test_summary(bundle_dir, referenced),
        "security_summaries": security_summary(bundle_dir, referenced),
        "migration_status": migration_status(bundle_dir),
        "release_smoke_results": release_smoke_summary(bundle_dir, referenced),
    }

    manifest = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "git": {
            "sha": git_value(["rev-parse", "HEAD"], "unknown"),
            "branch": git_value(["rev-parse", "--abbrev-ref", "HEAD"], "unknown"),
        },
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
        "commands": [result.__dict__ for result in command_results],
        "referenced_artifacts": referenced,
        "summaries": {
            key: (
                display_path(bundle_dir / value_path)
                if isinstance(value_path, Path)
                else "embedded"
            )
            for key, value_path in summaries.items()
        },
        "files": manifest_files(bundle_dir),
    }
    write_json(bundle_dir / "manifest.json", manifest)

    output_root.mkdir(parents=True, exist_ok=True)
    for stale_bundle in output_root.glob("evidence-bundle-*.tar.gz"):
        stale_bundle.unlink()
    tar_path = output_root / f"evidence-bundle-{sha}-{timestamp}.tar.gz"
    create_tarball(bundle_dir, tar_path)
    latest = output_root / "LATEST"
    latest.write_text(tar_path.name + "\n", encoding="utf-8")
    print(display_path(tar_path))
    return tar_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate consolidated audit/release evidence bundle"
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="timeout per evidence command in seconds",
    )
    args = parser.parse_args()
    build_bundle(args.output_root, args.work_root, args.timeout)
>>>>>>> theirs
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
