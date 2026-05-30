"""Structural Preflight Scanner for Fabric_4L / Value Fabric.

Phase 2 of structural hardening: Detect structural blockers before tests or code changes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    check_id: str
    severity: str  # critical, high, medium, info
    path: str
    finding_type: str
    message: str
    recommendation: str
    redacted_fingerprint: str | None = None


@dataclass
class PreflightReport:
    repo_root: str
    findings: list[Finding] = field(default_factory=list)
    strict_failures: int = 0
    exit_code: int = 0


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command safely, returning (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 2, "", "Command timed out"
    except FileNotFoundError:
        return 2, "", f"Command not found: {cmd[0]}"


def check_secret_file_risk(repo_root: Path, include_ignored: bool) -> list[Finding]:
    """Detect secret-risk filenames and git tracking state."""
    findings = []
    risky_patterns = [
        (r"\.env$", ".env file"),
        (r"\.env\.", ".env.* file"),
        (r"secrets?\.ya?ml$", "secrets YAML"),
        (r"secrets?\.json$", "secrets JSON"),
        (r".*\.pem$", "PEM certificate"),
        (r".*\.key$", "private key"),
        (r"k8s/.*secret", "k8s secret manifest"),
    ]

    # Get tracked files
    exit_code, stdout, _ = run_command(["git", "ls-files"], cwd=repo_root)
    if exit_code != 0:
        return [Finding(
            check_id="secret_file_risk",
            severity="high",
            path=".",
            finding_type="git_error",
            message="Could not list tracked files",
            recommendation="Ensure git is available and repo is valid",
        )]

    tracked_files = set(stdout.strip().split("\n"))

    for pattern, description in risky_patterns:
        for file_path in tracked_files:
            if re.search(pattern, file_path, re.IGNORECASE):
                findings.append(Finding(
                    check_id="secret_file_risk",
                    severity="critical",
                    path=file_path,
                    finding_type=f"tracked_{description}",
                    message=f"Tracked file matches secret-risk pattern: {description}",
                    recommendation="Remove from git, rotate secrets, add to .gitignore, use ExternalSecret",
                    redacted_fingerprint=f"[REDACTED:{file_path}]",
                ))

    # Check gitignore
    gitignore_path = repo_root / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
        required_patterns = [".env", ".env.*", "*.pem", "*.key"]
        for pattern in required_patterns:
            if pattern not in content:
                findings.append(Finding(
                    check_id="secret_file_risk",
                    severity="high",
                    path=".gitignore",
                    finding_type="missing_gitignore_pattern",
                    message=f"Pattern '{pattern}' not in .gitignore",
                    recommendation=f"Add '{pattern}' to .gitignore",
                ))

    return findings


def check_import_namespace_mismatch(repo_root: Path) -> list[Finding]:
    """Detect value_fabric vs value-fabric divergence."""
    findings = []

    hyphen_dir = repo_root / "value-fabric"
    underscore_dir = repo_root / "value_fabric"

    # Check what tests expect
    test_imports = []
    tests_dir = repo_root / "tests"
    if tests_dir.exists():
        for py_file in tests_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if "from value_fabric" in content or "import value_fabric" in content:
                    test_imports.append(str(py_file.relative_to(repo_root)))
            except Exception:
                pass

    if test_imports and not underscore_dir.exists():
        findings.append(Finding(
            check_id="import_namespace_mismatch",
            severity="critical",
            path="tests/",
            finding_type="missing_value_fabric_package",
            message=f"Tests import value_fabric but package doesn't exist. Files: {len(test_imports)}",
            recommendation="Create value_fabric/ compatibility package with forwarding imports",
        ))

    if hyphen_dir.exists() and underscore_dir.exists():
        # Check if underscore is a junction/pointer
        underscore_init = underscore_dir / "__init__.py"
        if underscore_init.exists():
            init_content = underscore_init.read_text(encoding="utf-8", errors="ignore")
            if not init_content.strip():
                findings.append(Finding(
                    check_id="import_namespace_mismatch",
                    severity="high",
                    path="value_fabric/__init__.py",
                    finding_type="empty_compatibility_package",
                    message="value_fabric/__init__.py is empty - needs forwarding imports",
                    recommendation="Add explicit imports to forward to value-fabric modules",
                ))

    # Test actual import
    exit_code, _, stderr = run_command(
        [sys.executable, "-c", "import value_fabric; print(value_fabric.__file__)"],
        cwd=repo_root
    )
    if exit_code != 0:
        findings.append(Finding(
            check_id="import_namespace_mismatch",
            severity="critical",
            path="value_fabric/",
            finding_type="import_resolution_failure",
            message="Cannot import value_fabric package",
            recommendation="Fix import path in pytest.ini or create proper package junctions",
        ))

    return findings


def check_namespace_shadowing(repo_root: Path) -> list[Finding]:
    """Detect legacy root value_fabric/shared/ that should have been removed."""
    findings = []

    root_shared = repo_root / "value_fabric" / "shared"
    pkg_shared = repo_root / "packages" / "shared" / "src" / "value_fabric" / "shared"

    if root_shared.exists():
        findings.append(Finding(
            check_id="namespace_shadowing",
            severity="high",
            path="value_fabric/shared/",
            finding_type="legacy_shared_remains",
            message="Root value_fabric/shared/ still exists",
            recommendation="Delete value_fabric/shared/ after confirming all code imports from packages/shared/src/value_fabric/shared/",
        ))

    if not pkg_shared.exists():
        findings.append(Finding(
            check_id="namespace_shadowing",
            severity="high",
            path="packages/shared/src/value_fabric/shared/",
            finding_type="canonical_shared_missing",
            message="Canonical shared package is missing",
            recommendation="Restore packages/shared/src/value_fabric/shared/",
        ))

    # Test where 'import value_fabric.shared' resolves
    exit_code, stdout, stderr = run_command(
        [sys.executable, "-c", "import value_fabric.shared; print(value_fabric.shared.__file__)"],
        cwd=repo_root
    )
    if exit_code == 0:
        resolved_path = stdout.strip()
        if "packages/shared/src/value_fabric/shared" not in resolved_path.replace("\\", "/"):
            findings.append(Finding(
                check_id="namespace_shadowing",
                severity="medium",
                path="value_fabric/shared/",
                finding_type="shared_resolves_to_wrong_location",
                message=f"import value_fabric.shared resolves to: {resolved_path}",
                recommendation="Ensure value_fabric.shared resolves to packages/shared/src/value_fabric/shared/",
            ))

    return findings


def check_pytest_config(repo_root: Path) -> list[Finding]:
    """Validate pytest.ini does not hide broken import topology."""
    findings = []

    pytest_ini = repo_root / "pytest.ini"
    pyproject_toml = repo_root / "pyproject.toml"

    config_file = None
    if pytest_ini.exists():
        config_file = pytest_ini
    elif pyproject_toml.exists():
        config_file = pyproject_toml

    if not config_file:
        findings.append(Finding(
            check_id="pytest_config",
            severity="high",
            path=".",
            finding_type="missing_pytest_config",
            message="No pytest.ini or pyproject.toml found",
            recommendation="Create pytest.ini with proper pythonpath configuration",
        ))
        return findings

    if config_file == pytest_ini:
        content = config_file.read_text(encoding="utf-8", errors="ignore")

        # Check pythonpath
        if "pythonpath" not in content:
            findings.append(Finding(
                check_id="pytest_config",
                severity="medium",
                path="pytest.ini",
                finding_type="missing_pythonpath",
                message="No pythonpath in pytest.ini",
                recommendation="Add pythonpath with . and layer src directories",
            ))
        elif "." not in content.split("pythonpath")[1].split("\n")[0] if "pythonpath" in content else False:
            findings.append(Finding(
                check_id="pytest_config",
                severity="medium",
                path="pytest.ini",
                finding_type="pythonpath_missing_dot",
                message="pythonpath should include . for proper imports",
                recommendation="Add . to pythonpath in pytest.ini",
            ))

    # Test pytest collection
    exit_code, stdout, stderr = run_command(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=repo_root
    )

    collection_errors = stderr.count("ERROR") + stderr.count("ImportError") + stderr.count("ModuleNotFoundError")
    if collection_errors > 0:
        findings.append(Finding(
            check_id="pytest_config",
            severity="critical",
            path="tests/",
            finding_type="collection_errors",
            message=f"pytest collection has {collection_errors} import errors",
            recommendation="Fix import topology before running tests",
        ))

    return findings


def check_tool_manifest_alignment(repo_root: Path) -> list[Finding]:
    """Compare registered tools with skill manifests."""
    findings = []

    # Count registered tools
    tools_init = repo_root / "services" / "layer4-agents" / "src" / "tools" / "__init__.py"
    skill_manifests_dir = repo_root / "services" / "layer4-agents" / "skills"

    if not tools_init.exists():
        findings.append(Finding(
            check_id="tool_manifest_alignment",
            severity="medium",
            path="services/layer4-agents/src/layer4_agents/tools/__init__.py",
            finding_type="missing_tools_init",
            message="Tools registry init not found",
            recommendation="Verify layer4-agents structure",
        ))
        return findings

    # Count skill manifests
    if skill_manifests_dir.exists():
        manifests = list(skill_manifests_dir.glob("*.md"))
        # This is a simplified check - real implementation would parse
        if len(manifests) < 5:
            findings.append(Finding(
                check_id="tool_manifest_alignment",
                severity="medium",
                path="services/layer4-agents/skills/",
                finding_type="few_skill_manifests",
                message=f"Only {len(manifests)} skill manifests found",
                recommendation="Ensure all tools have corresponding skill definitions",
            ))

    return findings


def check_ci_wiring(repo_root: Path) -> list[Finding]:
    """Verify structural checks are present in CI."""
    findings = []

    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.exists():
        findings.append(Finding(
            check_id="ci_wiring",
            severity="high",
            path=".github/workflows/",
            finding_type="missing_workflows_dir",
            message="No GitHub workflows directory",
            recommendation="Create CI workflows for automated checks",
        ))
        return findings

    # Check for preflight workflow
    preflight_workflow = workflows_dir / "preflight.yml"
    pr_checks = workflows_dir / "pr-checks.yml"

    has_structural_check = False
    for workflow_file in workflows_dir.glob("*.yml"):
        content = workflow_file.read_text(encoding="utf-8", errors="ignore")
        if "structural_preflight" in content or "python_contract_lint" in content:
            has_structural_check = True
            break

    if not has_structural_check:
        findings.append(Finding(
            check_id="ci_wiring",
            severity="high",
            path=".github/workflows/",
            finding_type="missing_structural_checks",
            message="No CI workflow runs structural_preflight.py or python_contract_lint.py",
            recommendation="Add structural checks to pr-checks.yml or create preflight.yml",
        ))

    return findings


def check_hardcoded_db_credentials(repo_root: Path) -> list[Finding]:
    """Detect hardcoded postgres:postgres credentials in K8s manifests and configs.

    Hardcoded credentials in K8s manifests are exposed to anyone with read access to
    the repo AND to anyone who can run `kubectl describe pod`. They must always be
    injected via secretKeyRef.
    """
    findings: list[Finding] = []
    # Pattern: literal postgres:postgres in a URL string (catches the most common form)
    credential_pattern = re.compile(
        r"postgres:postgres@|:[Pp]assword@|postgresql://\w+:\w+@"
    )
    # Only scan infrastructure files (K8s manifests, Docker Compose, shell scripts)
    scan_dirs = ["k8s", "infra", "scripts"]
    scan_suffixes = {".yml", ".yaml", ".sh", ".env.example"}

    for scan_dir in scan_dirs:
        target = repo_root / scan_dir
        if not target.is_dir():
            continue
        for file in target.rglob("*"):
            # Skip template files that intentionally document the pattern
            if file.suffix not in scan_suffixes:
                continue
            if "secrets.yml.template" in file.name or "secrets.yaml.template" in file.name:
                continue
            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(content.splitlines(), start=1):
                if credential_pattern.search(line):
                    findings.append(Finding(
                        check_id="hardcoded_db_credentials",
                        severity="critical",
                        path=f"{file.relative_to(repo_root)}:{i}",
                        finding_type="hardcoded_credentials",
                        message=(
                            f"Hardcoded database credentials detected at line {i}. "
                            "Use secretKeyRef to inject credentials from a K8s Secret."
                        ),
                        recommendation=(
                            "Replace `value: \"postgresql://user:pass@...\"` with "
                            "`valueFrom: secretKeyRef: name: <secret> key: <key>` and "
                            "add the corresponding Secret to k8s/secrets.yml.template."
                        ),
                    ))
    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Structural preflight scanner for Fabric_4L"
    )
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--strict", action="store_true", help="Fail on any blocker")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--include-ignored", action="store_true", help="Include gitignored files")
    parser.add_argument("--no-content-secret-scan", action="store_true", help="Skip content scanning")

    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    # Run all checks
    all_findings = []
    all_findings.extend(check_secret_file_risk(repo_root, args.include_ignored))
    all_findings.extend(check_import_namespace_mismatch(repo_root))
    all_findings.extend(check_namespace_shadowing(repo_root))
    all_findings.extend(check_pytest_config(repo_root))
    all_findings.extend(check_tool_manifest_alignment(repo_root))
    all_findings.extend(check_ci_wiring(repo_root))
    all_findings.extend(check_hardcoded_db_credentials(repo_root))

    # Determine strict failures
    strict_failures = [f for f in all_findings if f.severity in ("critical", "high")]

    report = PreflightReport(
        repo_root=str(repo_root),
        findings=all_findings,
        strict_failures=len(strict_failures),
        exit_code=1 if (args.strict and strict_failures) else 0,
    )

    # Output
    if args.json:
        print(json.dumps({
            "repo_root": report.repo_root,
            "exit_code": report.exit_code,
            "strict_failures": report.strict_failures,
            "findings": [asdict(f) for f in report.findings],
        }, indent=2))
    else:
        print(f"\n{'='*60}")
        print("STRUCTURAL PREFLIGHT REPORT")
        print(f"{'='*60}")
        print(f"Repository: {report.repo_root}")
        print(f"Total findings: {len(report.findings)}")
        print(f"Strict failures: {report.strict_failures}")
        print(f"Exit code: {report.exit_code}")
        print(f"{'='*60}\n")

        if report.findings:
            print("FINDINGS BY SEVERITY:\n")
            for severity in ["critical", "high", "medium", "info"]:
                findings = [f for f in report.findings if f.severity == severity]
                if findings:
                    print(f"\n{severity.upper()} ({len(findings)}):")
                    for f in findings:
                        print(f"  [{f.check_id}] {f.path}")
                        print(f"    Type: {f.finding_type}")
                        print(f"    Message: {f.message}")
                        print(f"    Recommendation: {f.recommendation}")
                        if f.redacted_fingerprint:
                            print(f"    Fingerprint: {f.redacted_fingerprint}")
        else:
            print("No structural issues found!")

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
