"""Python Contract Linter for Fabric_4L / Value Fabric.

Phase 3: Enforce Python-side architectural contracts (tenant_id misuse, raw DB connections, etc.)
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from datetime import date
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Pattern


@dataclass
class ContractFinding:
    contract_id: str
    severity: str  # critical, high, medium, low
    path: str
    line: int
    column: int
    message: str
    preferred_pattern: str
    snippet: str | None = None


@dataclass
class LintReport:
    repo_root: str
    files_scanned: int = 0
    findings: list[ContractFinding] = field(default_factory=list)
    exit_code: int = 0


@dataclass(frozen=True)
class RegexCheck:
    contract_id: str
    severity: str
    pattern: Pattern[str]
    description: str
    preferred_pattern: str


CONTRACT_CHECKS: dict[str, dict[str, Any]] = {
    "tenant_context": {
        "severity": "critical",
        "patterns": [
            (r"request\.headers\[[\x27\x22]x-tenant-id[\x27\x22]\]", "direct header access for tenant"),
            (r"request\.headers\.get\([\x27\x22]x-tenant-id[\x27\x22]", "direct header get for tenant"),
        ],
        "preferred_pattern": "Use get_tenant_context() or middleware-resolved tenant",
    },
    "raw_db_connection": {
        "severity": "critical",
        "patterns": [
            (r"psycopg2\.connect", "psycopg2 direct connect"),
            (r"asyncpg\.connect", "asyncpg direct connect"),
            (r"pymysql\.connect", "pymysql direct connect"),
            (r"create_engine\s*\(", "create_engine outside approved modules"),
            (r"postgresql://[^\s\"']+", "hardcoded postgres URL"),
            (r"mysql://[^\s\"']+", "hardcoded mysql URL"),
        ],
        "preferred_pattern": "Use get_db_from_context() or approved database provider",
    },
    "secret_in_source": {
        "severity": "critical",
        "patterns": [
            (r"['\"]sk-[a-zA-Z0-9]{20,}['\"]", "OpenAI API key pattern"),
            (r"['\"]AKIA[0-9A-Z]{16}['\"]", "AWS access key pattern"),
            (r"['\"][0-9a-f]{32,}['\"].*secret", "hex secret near 'secret' keyword"),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "hardcoded password"),
            (r"PASSWORD\s*=\s*['\"][^'\"]+['\"]", "hardcoded PASSWORD"),
            (r"SECRET\s*=\s*['\"][^'\"]+['\"]", "hardcoded SECRET"),
            (r"TOKEN\s*=\s*['\"][^'\"]{8,}['\"]", "hardcoded TOKEN"),
        ],
        "preferred_pattern": "Load from environment variables, ExternalSecrets, or Vault",
    },
    "tool_error_contract": {
        "severity": "high",
        "patterns": [
            (r"except\s+Exception\s*:\s*pass", "bare except with pass"),
        ],
        "preferred_pattern": "Return ToolResult with status='error' and safe error message",
    },
    "no_fix_imports": {
        "severity": "high",
        "patterns": [],
        "preferred_pattern": "Move production imports to stable module names (for example, telemetry.py)",
    },
    "security_todo": {
        "severity": "medium",
        "patterns": [
            (r"#\s*TODO.*auth", "TODO near auth"),
            (r"#\s*TODO.*tenant", "TODO near tenant"),
            (r"#\s*FIXME.*auth", "FIXME near auth"),
            (r"#\s*FIXME.*tenant", "FIXME near tenant"),
            (r"skip.*security.*check", "skip security check"),
            (r"bypass.*auth", "auth bypass"),
            (r"dev.*only.*auth", "dev-only auth"),
        ],
        "preferred_pattern": "Remove or track security-sensitive TODOs before production",
    },
}

REGEX_CHECKS: tuple[RegexCheck, ...] = tuple(
    RegexCheck(
        contract_id=contract_id,
        severity=str(config["severity"]),
        pattern=re.compile(pattern, re.IGNORECASE),
        description=description,
        preferred_pattern=str(config["preferred_pattern"]),
    )
    for contract_id, config in CONTRACT_CHECKS.items()
    for pattern, description in config.get("patterns", [])
)

SCAN_GLOBS = (
    "services/**/*.py",
    "packages/shared/src/value_fabric/shared/**/*.py",
    "tests/**/*.py",
)
RELEASE_SCOPED_PREFIXES = (
    "services/",
    "value_fabric/",
    "packages/shared/src/value_fabric/shared/",
    "k8s/",
    "config/production-readiness/",
)
SECURITY_CRITICAL_TODO_PATTERN = re.compile(
    r"\b(?:TODO|FIXME)\b[^\n#]*\b(?:auth|authentication|authorization|tenant|rbac|acl|oidc)\b|\bSECURITY-TODO\b",
    re.IGNORECASE,
)
AUTH_TENANT_EXCEPTION_TAG_PATTERN = re.compile(
    r"\[auth-tenant-exception\s+ticket=(?P<ticket>[A-Z][A-Z0-9_-]+-\d+)\s+owner=(?P<owner>[a-z0-9][a-z0-9._-]*)\s+expiry=(?P<expiry>\d{4}-\d{2}-\d{2})\]",
    re.IGNORECASE,
)

DEPRECATED_DB_DEP_ALLOWLIST = {
    "services/layer4-agents/src/database.py",
    "tests/security/test_deprecated_l4_db_dependencies.py",
}

APPROVED_RAW_DB_PATH_PARTS = (
    "/config/",
    "/database.py",
    "/database/",
    "/db/",
    "/migrations/env.py",
    "/shared/config.py",
)

APPROVED_TENANT_HEADER_PATH_PARTS = (
    "/api/auth.py",
    "/api/auth_context.py",
    "/api/tenant_context.py",
    "/boundaries/tenant_boundary.py",
    "/core/tenant_context.py",
    "/security/dil_auth.py",
)

TOOL_EXECUTION_FUNCTION_NAMES = frozenset(
    {
        "__call__",
        "_execute",
        "_execute_tool",
        "execute",
        "execute_tool",
        "run_tool",
    }
)

ALLOWED_TOOL_RAISE_EXCEPTIONS = frozenset(
    {
        "HTTPException",
        "NotImplementedError",
        "ProviderNotImplementedError",
        # Structured tool validation error: BaseTool.run maps this to the stable
        # TENANT_SPOOFING_DETECTED failure code without logging an exception stack trace.
        "TenantSpoofingError",
    }
)

SKIP_PATH_PARTS = frozenset(
    {
        "__pycache__",
        ".eggs",
        "dist",
        "build",
        ".tox",
        ".venv",
        "venv",
        "node_modules",
    }
)


def is_test_or_stub_file(file_path: Path) -> bool:
    """Check if file is a test or stub that might legitimately have certain patterns."""
    name = file_path.name.lower()
    path_parts = {part.lower() for part in file_path.parts}
    return (
        "tests" in path_parts
        or "test" in path_parts
        or "test_" in name
        or "_test.py" in name
        or name.startswith("test")
        or "stub" in name
        or "mock" in name
    )


def _is_false_positive(file_path: Path, contract_id: str, line: str) -> bool:
    line_lower = line.lower()
    if "example" in line_lower or "placeholder" in line_lower:
        return True
    if "CHANGE_ME" in line or "fake" in line_lower:
        return True
    if contract_id == "secret_in_source" and is_test_or_stub_file(file_path):
        return True
    if contract_id == "secret_in_source":
        assignment = re.search(r"=\s*['\"](?P<value>[^'\"]+)['\"]", line)
        if assignment is not None:
            value = assignment.group("value")
            lhs = re.search(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=", line)
            if lhs is not None and value.lower() == lhs.group("name").lower():
                return True
            if value.lower() in {"invalid_token"}:
                return True
            if re.fullmatch(r"[A-Z][A-Z0-9_]+", value):
                return True
            if "dev" in value.lower() and "change" in value.lower():
                return True
    return False


def _is_docstring_or_example_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(('"""', "'''")):
        return True
    return stripped.startswith(('"', "'")) and "=" not in stripped


def _is_approved_raw_db_connection_path(file_path: Path) -> bool:
    path = file_path.as_posix().lower()
    if is_test_or_stub_file(file_path):
        return True
    return any(part in path for part in APPROVED_RAW_DB_PATH_PARTS)


def _is_approved_tenant_header_path(file_path: Path) -> bool:
    path = file_path.as_posix().lower()
    return any(part in path for part in APPROVED_TENANT_HEADER_PATH_PARTS)


def _docstring_line_numbers(content: str) -> set[int]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr):
            continue
        if not isinstance(first.value, ast.Constant) or not isinstance(first.value.value, str):
            continue
        start = getattr(first, "lineno", 0)
        end = getattr(first, "end_lineno", start)
        lines.update(range(start, end + 1))
    return lines


def _module_has_fix_component(module: str | None) -> bool:
    if not module:
        return False
    for component in module.split("."):
        component = component.lower()
        if component == "fix" or component.startswith("fix_") or component.endswith("_fix"):
            return True
    return False


def _is_tool_execution_path(file_path: Path) -> bool:
    path = file_path.as_posix().lower()
    return "/tools/" in path or path.endswith("_tools.py") or path.endswith("/tools.py")


def _raised_exception_name(node: ast.Raise) -> str | None:
    exc = node.exc
    if exc is None:
        return None
    if isinstance(exc, ast.Call):
        exc = exc.func
    if isinstance(exc, ast.Name):
        return exc.id
    if isinstance(exc, ast.Attribute):
        return exc.attr
    return None


def _raises_guarded_by_exception_handler(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[int]:
    guarded: set[int] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Try):
            catches_error = any(
                handler.type is None
                or (
                    isinstance(handler.type, ast.Name)
                    and handler.type.id in {"Exception", "BaseException", "ValueError"}
                )
                for handler in node.handlers
            )
            if catches_error:
                for body_node in node.body:
                    guarded.update(id(child) for child in ast.walk(body_node) if isinstance(child, ast.Raise))
            # Re-raising asyncio.CancelledError inside its own handler is required
            # hygiene (PEP 3156) and is not an unstructured tool error.
            for handler in node.handlers:
                if handler.type is None:
                    continue
                if isinstance(handler.type, ast.Name) and handler.type.id in {"CancelledError", "asyncio.CancelledError", "BaseException"}:
                    guarded.update(id(child) for child in ast.walk(handler) if isinstance(child, ast.Raise))
                elif isinstance(handler.type, ast.Attribute) and handler.type.attr == "CancelledError":
                    guarded.update(id(child) for child in ast.walk(handler) if isinstance(child, ast.Raise))
                elif isinstance(handler.type, ast.Tuple):
                    names = {
                        elt.attr if isinstance(elt, ast.Attribute) else elt.id
                        for elt in handler.type.elts
                        if isinstance(elt, (ast.Name, ast.Attribute))
                    }
                    if names & {"CancelledError", "asyncio.CancelledError", "BaseException"}:
                        guarded.update(id(child) for child in ast.walk(handler) if isinstance(child, ast.Raise))
        elif isinstance(node, ast.ExceptHandler):
            # Stand-alone except handlers are not expected at function scope, but
            # guard them consistently if they explicitly catch cancellation.
            if node.type is None:
                continue
            if isinstance(node.type, ast.Name) and node.type.id in {"CancelledError", "asyncio.CancelledError", "BaseException"}:
                guarded.update(id(child) for child in ast.walk(node) if isinstance(child, ast.Raise))
            elif isinstance(node.type, ast.Attribute) and node.type.attr == "CancelledError":
                guarded.update(id(child) for child in ast.walk(node) if isinstance(child, ast.Raise))
            elif isinstance(node.type, ast.Tuple):
                names = {
                    elt.attr if isinstance(elt, ast.Attribute) else elt.id
                    for elt in node.type.elts
                    if isinstance(elt, (ast.Name, ast.Attribute))
                }
                if names & {"CancelledError", "asyncio.CancelledError", "BaseException"}:
                    guarded.update(id(child) for child in ast.walk(node) if isinstance(child, ast.Raise))
    return guarded


def check_file_with_regex(file_path: Path, content: str) -> list[ContractFinding]:
    """Check file using precompiled regex patterns with a single pass over lines."""
    findings: list[ContractFinding] = []
    docstring_lines = _docstring_line_numbers(content)

    for line_number, line in enumerate(content.splitlines(), start=1):
        if line_number in docstring_lines:
            continue
        normalized_path = file_path.as_posix()
        if normalized_path.startswith(RELEASE_SCOPED_PREFIXES) and SECURITY_CRITICAL_TODO_PATTERN.search(line):
            metadata_match = AUTH_TENANT_EXCEPTION_TAG_PATTERN.search(line)
            has_valid_metadata = False
            if metadata_match is not None:
                try:
                    has_valid_metadata = date.fromisoformat(metadata_match.group("expiry")) >= date.today()
                except ValueError:
                    has_valid_metadata = False
            if not has_valid_metadata:
                findings.append(
                    ContractFinding(
                        contract_id="security_todo",
                        severity="critical",
                        path=str(file_path),
                        line=line_number,
                        column=0,
                        message="Security-critical TODO/FIXME in release-scoped path is missing valid exception metadata",
                        preferred_pattern=(
                            "Include [auth-tenant-exception ticket=SEC-123 owner=team.slug expiry=YYYY-MM-DD] "
                            "or remove the marker"
                        ),
                        snippet=line.strip()[:100],
                    )
                )
                continue
            findings.append(
                ContractFinding(
                    contract_id="security_todo",
                    severity="critical",
                    path=str(file_path),
                    line=line_number,
                    column=0,
                    message="Unresolved security-critical TODO/FIXME marker in release-scoped path",
                    preferred_pattern="Replace marker with ticket ID, owner team, and target milestone",
                    snippet=line.strip()[:100],
                )
            )
            continue

        code_part = line.split("#", 1)[0]
        if not code_part and not line.lstrip().startswith(('#', '"', "'")):
            continue
        if _is_docstring_or_example_line(code_part):
            continue

        for check in REGEX_CHECKS:
            if is_test_or_stub_file(file_path) and check.contract_id in {
                "raw_db_connection",
                "secret_in_source",
                "tenant_context",
                "tool_error_contract",
            }:
                continue
            if check.contract_id == "raw_db_connection" and _is_approved_raw_db_connection_path(file_path):
                continue
            if check.contract_id == "tenant_context" and _is_approved_tenant_header_path(file_path):
                continue
            match = check.pattern.search(code_part)
            if match is None:
                continue
            if _is_false_positive(file_path, check.contract_id, line):
                continue

            findings.append(
                ContractFinding(
                    contract_id=check.contract_id,
                    severity=check.severity,
                    path=str(file_path),
                    line=line_number,
                    column=match.start(),
                    message=f"Found: {check.description}",
                    preferred_pattern=check.preferred_pattern,
                    snippet=line.strip()[:100],
                )
            )

    return findings


def check_file_with_ast(file_path: Path, content: str) -> list[ContractFinding]:
    """Check file using AST analysis."""
    findings: list[ContractFinding] = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return findings  # Skip files with syntax errors

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules: list[str | None] = []
            if isinstance(node, ast.ImportFrom):
                modules.append(node.module)
            else:
                modules.extend(alias.name for alias in node.names)
            if any(_module_has_fix_component(module) for module in modules):
                findings.append(
                    ContractFinding(
                        contract_id="no_fix_imports",
                        severity="high",
                        path=str(file_path),
                        line=getattr(node, "lineno", 0),
                        column=getattr(node, "col_offset", 0),
                        message="Import from fix module detected",
                        preferred_pattern="Move production imports to stable module names (for example, telemetry.py)",
                    )
                )

    if _is_tool_execution_path(file_path) and not is_test_or_stub_file(file_path):
        for function in (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))):
            if function.name not in TOOL_EXECUTION_FUNCTION_NAMES:
                continue
            guarded_raises = _raises_guarded_by_exception_handler(function)
            for child in ast.walk(function):
                if not isinstance(child, ast.Raise):
                    continue
                if id(child) in guarded_raises:
                    continue
                exception_name = _raised_exception_name(child)
                if exception_name in ALLOWED_TOOL_RAISE_EXCEPTIONS:
                    continue
                findings.append(
                    ContractFinding(
                        contract_id="tool_error_contract",
                        severity="high",
                        path=str(file_path),
                        line=getattr(child, "lineno", 0),
                        column=getattr(child, "col_offset", 0),
                        message="Unstructured raise in tool execution function",
                        preferred_pattern="Return ToolResult with status='error'",
                    )
                )

    return findings


def check_deprecated_l4_db_dependencies(file_path: Path, content: str, repo_root: Path) -> list[ContractFinding]:
    """Block deprecated Layer 4 DB dependency imports/usages outside allowlist."""
    repo_relative = file_path.relative_to(repo_root).as_posix()
    if repo_relative in DEPRECATED_DB_DEP_ALLOWLIST or is_test_or_stub_file(file_path):
        return []

    findings: list[ContractFinding] = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names = {alias.name for alias in node.names}
            if {"get_db", "get_db_with_tenant"} & names:
                findings.append(
                    ContractFinding(
                        contract_id="deprecated_l4_db_dependency",
                        severity="critical",
                        path=repo_relative,
                        line=getattr(node, "lineno", 0),
                        column=getattr(node, "col_offset", 0),
                        message="Deprecated Layer 4 DB dependency import detected",
                        preferred_pattern="Use get_db_from_context()",
                    )
                )
        if isinstance(node, ast.Name) and node.id in {"get_db", "get_db_with_tenant"}:
            findings.append(
                ContractFinding(
                    contract_id="deprecated_l4_db_dependency",
                    severity="critical",
                    path=repo_relative,
                    line=getattr(node, "lineno", 0),
                    column=getattr(node, "col_offset", 0),
                    message=f"Deprecated Layer 4 DB dependency usage detected: {node.id}",
                    preferred_pattern="Use get_db_from_context()",
                )
            )
    return findings


def should_scan_file(file_path: Path) -> bool:
    """Determine if a file should be scanned."""
    if file_path.suffix != ".py":
        return False

    path_parts = set(file_path.parts)
    if path_parts & SKIP_PATH_PARTS:
        return False

    return "migrations/versions" not in file_path.as_posix()


def _within_scan_scope(path: Path, repo_root: Path) -> bool:
    """Return True when a path belongs to the same roots used by full scans."""
    try:
        rel = path.relative_to(repo_root).as_posix()
    except ValueError:
        return False
    return rel.startswith(("services/", "packages/shared/src/value_fabric/shared/", "tests/"))


def _changed_python_files(repo_root: Path) -> list[Path]:
    """Return changed Python files from git when --changed-only is requested."""
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    files: list[Path] = []
    for raw_path in completed.stdout.splitlines():
        path = repo_root / raw_path
        if path.exists() and should_scan_file(path) and _within_scan_scope(path, repo_root):
            files.append(path)
    return sorted(set(files))


def _all_python_files(repo_root: Path) -> list[Path]:
    python_files: set[Path] = set()
    for pattern in SCAN_GLOBS:
        python_files.update(path for path in repo_root.glob(pattern) if should_scan_file(path))
    return sorted(python_files)


def _iter_scan_files(repo_root: Path, changed_only: bool) -> Iterable[Path]:
    if changed_only:
        return _changed_python_files(repo_root)
    return _all_python_files(repo_root)


def scan_repository(repo_root: Path, changed_only: bool = False) -> LintReport:
    """Scan repository for contract violations."""
    report = LintReport(repo_root=str(repo_root))

    for file_path in _iter_scan_files(repo_root, changed_only):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        report.files_scanned += 1
        report.findings.extend(check_file_with_regex(file_path, content))
        report.findings.extend(check_file_with_ast(file_path, content))
        report.findings.extend(check_deprecated_l4_db_dependencies(file_path, content, repo_root))

    return report


def load_baseline(baseline_path: Path) -> set[str]:
    """Load baseline findings to ignore."""
    if not baseline_path.exists():
        return set()

    try:
        data = json.loads(baseline_path.read_text())
        return set(data.get("findings", []))
    except Exception:
        return set()


def filter_with_baseline(
    findings: list[ContractFinding], baseline: set[str], repo_root: Path
) -> list[ContractFinding]:
    """Filter out baseline findings."""
    filtered = []
    for finding in findings:
        absolute_key = f"{finding.path}:{finding.line}:{finding.contract_id}"
        try:
            relative_path = Path(finding.path).resolve().relative_to(repo_root).as_posix()
        except ValueError:
            relative_path = finding.path
        relative_key = f"{relative_path}:{finding.line}:{finding.contract_id}"
        if absolute_key not in baseline and relative_key not in baseline:
            filtered.append(finding)
    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Python contract linter for Fabric_4L"
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--strict", action="store_true", help="Fail on any critical/high")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--baseline", help="Path to baseline file")
    parser.add_argument("--changed-only", action="store_true", help="Only scan changed files")

    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    # Scan repository
    report = scan_repository(repo_root, args.changed_only)

    # Apply baseline if provided
    if args.baseline:
        baseline = load_baseline(Path(args.baseline))
        report.findings = filter_with_baseline(report.findings, baseline, repo_root)

    # Determine exit code
    severity_counts = {
        severity: sum(1 for finding in report.findings if finding.severity == severity)
        for severity in ("critical", "high", "medium", "low")
    }
    report.exit_code = 1 if (args.strict and (severity_counts["critical"] or severity_counts["high"])) else 0

    # Output
    if args.json:
        print(
            json.dumps(
                {
                    "repo_root": report.repo_root,
                    "files_scanned": report.files_scanned,
                    "exit_code": report.exit_code,
                    "findings_by_severity": severity_counts,
                    "findings": [asdict(f) for f in report.findings],
                },
                indent=2,
            )
        )
    else:
        print(f"\n{'='*60}")
        print("PYTHON CONTRACT LINT REPORT")
        print(f"{'='*60}")
        print(f"Repository: {report.repo_root}")
        print(f"Files scanned: {report.files_scanned}")
        print(f"Total findings: {len(report.findings)}")

        # Severity breakdown
        for severity in ["critical", "high", "medium", "low"]:
            count = severity_counts[severity]
            if count > 0:
                print(f"  {severity.upper()}: {count}")

        print(f"Exit code: {report.exit_code}")
        print(f"{'='*60}\n")

        if report.findings:
            print("FINDINGS:\n")
            for finding in sorted(report.findings, key=lambda f: (f.severity, f.path)):
                print(f"[{finding.severity.upper()}] {finding.contract_id}")
                print(f"  File: {finding.path}:{finding.line}")
                print(f"  Message: {finding.message}")
                print(f"  Preferred: {finding.preferred_pattern}")
                if finding.snippet:
                    print(f"  Snippet: {finding.snippet}")
                print()

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
