"""Pre-seeded finding catalog for the AuditOrchestrator agent.

The catalog defines 44 stable findings (roughly 4–5 per audit area) with
lightweight, read-only checks. Each check returns structured evidence that
is used to instantiate a :class:`Finding` from ``models.py``.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ..models import AuditArea, AuditConfig, Confidence, Finding, Severity

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tmp",
    "archive",
    "artifacts",
    "dist",
    "build",
}


def _is_excluded(path: Path) -> bool:
    """Return True if any path component should be skipped."""
    return any(part in _EXCLUDED_DIRS for part in path.parts)


def _walk_files(
    repo_path: Path,
    roots: list[Path] | None = None,
    extensions: set[str] | None = None,
) -> list[Path]:
    """Walk configured roots while pruning excluded directories.

    This avoids descending into ``node_modules``, ``.venv``, ``.git``, etc.,
    which keeps large repository scans fast.
    """
    results: list[Path] = []
    search_roots = roots or [repo_path]
    for root in search_roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
            # Prune excluded directories in-place so os.walk does not descend.
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if extensions is None or file_path.suffix.lower() in extensions:
                    results.append(file_path)
    return results


def _source_files(repo_path: Path, extensions: set[str]) -> list[Path]:
    """Yield non-excluded source files with the given extensions."""
    return _walk_files(repo_path, extensions=extensions)


def _py_files(repo_path: Path) -> list[Path]:
    return _source_files(repo_path, {".py"})


def _read_lines(path: Path) -> list[str]:
    """Read a text file, returning a list of lines.

    Errors are ignored so that binary or malformed files do not abort a run.
    Caching is intentionally avoided here: a process-wide cache would retain
    stale file contents across audit runs and across different repositories.
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            return fh.readlines()
    except (OSError, UnicodeDecodeError):
        return []


def _line_count(path: Path) -> int:
    return len(_read_lines(path))


def _match_count(files: list[Path], pattern: re.Pattern[str]) -> tuple[int, list[str]]:
    """Count lines matching ``pattern`` across ``files``.

    Returns the total count plus a bounded list of evidence snippets.
    """
    total = 0
    snippets: list[str] = []
    for file_path in files:
        try:
            for i, line in enumerate(_read_lines(file_path), start=1):
                if pattern.search(line):
                    total += 1
                    if len(snippets) < 10:
                        snippets.append(f"{file_path}:{i}")
        except OSError:
            continue
    return total, snippets


def _load_yaml(path: Path) -> dict[str, Any] | None:
    """Load a YAML file if it exists and is parseable."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _find_pyprojects(repo_path: Path) -> list[Path]:
    return [p for p in repo_path.rglob("pyproject.toml") if not _is_excluded(p)]


def _pyproject_sections(repo_path: Path, section: str) -> list[tuple[Path, Any]]:
    """Return all ``[tool.*]`` sections with a given name from pyproject files."""
    found: list[tuple[Path, Any]] = []
    for pyproject in _find_pyprojects(repo_path):
        data = _load_yaml(pyproject)
        if not data:
            continue
        tool = data.get("tool", {})
        if section in tool:
            found.append((pyproject, tool[section]))
    return found


# ---------------------------------------------------------------------------
# Catalog checks
# ---------------------------------------------------------------------------


def _check_oversized_python(repo_path: Path, config: AuditConfig) -> dict[str, Any]:
    threshold = config.max_file_size_lines
    oversized: list[str] = []
    for file_path in _py_files(repo_path):
        count = _line_count(file_path)
        if count > threshold:
            oversized.append(f"{file_path}:{count}")
    return {
        "triggered": bool(oversized),
        "evidence": "; ".join(oversized[:10]) if oversized else "",
        "check_output": f"{len(oversized)} Python files exceed {threshold} lines",
        "oversized_python_modules": len(oversized),
        "observed_fact": f"{len(oversized)} Python module(s) exceed {threshold} lines.",
    }


def _check_oversized_frontend(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    threshold = 800
    oversized: list[str] = []
    for file_path in _source_files(repo_path, {".js", ".jsx", ".ts", ".tsx", ".vue"}):
        count = _line_count(file_path)
        if count > threshold:
            oversized.append(f"{file_path}:{count}")
    return {
        "triggered": bool(oversized),
        "evidence": "; ".join(oversized[:10]) if oversized else "",
        "check_output": f"{len(oversized)} frontend files exceed {threshold} lines",
        "oversized_js_modules": len(oversized),
        "observed_fact": f"{len(oversized)} frontend file(s) exceed {threshold} lines.",
    }


def _check_duplicate_files(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    """Detect duplicate source files by content hash within services and apps."""
    hashes: dict[str, list[Path]] = {}
    search_roots = [
        repo_path / "services",
        repo_path / "apps",
        repo_path / "packages",
    ]
    files = _walk_files(
        repo_path,
        roots=[r for r in search_roots if r.exists()],
        extensions={".py", ".js", ".ts", ".tsx", ".yaml", ".yml", ".json"},
    )
    for file_path in files:
        try:
            content = file_path.read_bytes()
        except OSError:
            continue
        if not content:
            continue
        digest = hashlib.md5(content, usedforsecurity=False).hexdigest()
        hashes.setdefault(digest, []).append(file_path)

    duplicate_groups = [paths for paths in hashes.values() if len(paths) > 1]
    evidence = "; ".join(
        f"{', '.join(str(p) for p in group[:3])}" for group in duplicate_groups[:5]
    )
    return {
        "triggered": bool(duplicate_groups),
        "evidence": evidence,
        "check_output": f"{len(duplicate_groups)} groups of duplicate files detected",
        "duplicate_file_groups": len(duplicate_groups),
        "duplicate_file_count": len(duplicate_groups),
        "observed_fact": f"{len(duplicate_groups)} group(s) of duplicate source files detected.",
    }


def _check_deep_nesting(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    deep: list[str] = []
    search_roots = [repo_path / "services", repo_path / "apps", repo_path / "packages"]
    files = _walk_files(repo_path, roots=[r for r in search_roots if r.exists()])
    for file_path in files:
        for root in search_roots:
            try:
                rel = file_path.relative_to(root)
                depth = len(rel.parts)
                if depth > 8:
                    deep.append(f"{file_path} (depth {depth})")
                break
            except ValueError:
                continue
    return {
        "triggered": len(deep) > 10,
        "evidence": "; ".join(deep[:10]) if deep else "",
        "check_output": f"{len(deep)} files nested deeper than 8 levels",
        "deeply_nested_files": len(deep),
        "observed_fact": f"{len(deep)} files are located more than 8 directories deep.",
    }


_CROSS_LAYER_RE = re.compile(r"(?:from|import)\s+layer\d+(?![_\w-])")


def _check_service_boundaries(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    services_dir = repo_path / "services"
    if not services_dir.exists():
        return {"triggered": False, "cross_layer_imports": 0}
    total, snippets = _match_count(_py_files(repo_path), _CROSS_LAYER_RE)
    return {
        "triggered": total > 0,
        "evidence": "; ".join(snippets[:10]),
        "check_output": f"{total} cross-layer import statements found",
        "cross_layer_imports": total,
        "observed_fact": f"{total} cross-layer import statement(s) found.",
    }


_RELATIVE_IMPORT_RE = re.compile(r"^\s*from\s+\.")


def _check_relative_imports(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    total, snippets = _match_count(_py_files(repo_path), _RELATIVE_IMPORT_RE)
    return {
        "triggered": total > 20,
        "evidence": f"{total} relative imports; examples: " + "; ".join(snippets[:5]),
        "check_output": f"{total} relative import statements",
        "relative_import_count": total,
        "observed_fact": f"{total} relative import statement(s) detected across Python source.",
    }


_BARE_EXCEPT_RE = re.compile(r"^\s*except\s*:\s*")


def _check_bare_excepts(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    total, snippets = _match_count(_py_files(repo_path), _BARE_EXCEPT_RE)
    return {
        "triggered": total > 0,
        "evidence": "; ".join(snippets[:10]),
        "check_output": f"{total} bare except clauses found",
        "bare_except_count": total,
        "observed_fact": f"{total} bare ``except:`` clause(s) detected.",
    }


def _check_mypy_disabled(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    disabled: list[str] = []
    disabled_code_count = 0
    for pyproject, mypy in _pyproject_sections(repo_path, "mypy"):
        if mypy.get("disable_error_code"):
            disabled.append(f"{pyproject}: disable_error_code={mypy['disable_error_code']}")
            error_codes = mypy["disable_error_code"]
            if isinstance(error_codes, list):
                disabled_code_count += len(error_codes)
            else:
                # Treat a single string/code as one disabled code.
                disabled_code_count += 1
        if mypy.get("ignore_missing_imports"):
            disabled.append(f"{pyproject}: ignore_missing_imports=true")
            disabled_code_count += 1
    return {
        "triggered": bool(disabled),
        "evidence": "; ".join(disabled[:5]),
        "check_output": f"{disabled_code_count} mypy error codes disabled",
        "mypy_disabled_codes": disabled_code_count,
        "observed_fact": f"{disabled_code_count} mypy error code(s) are disabled across configuration files.",
    }


def _check_ruff_sprawl(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    ignores = 0
    per_file = 0
    details: list[str] = []
    for pyproject, ruff in _pyproject_sections(repo_path, "ruff"):
        lint = ruff.get("lint", {}) if isinstance(ruff, dict) else {}
        ignore_list = lint.get("ignore", [])
        ignores += len(ignore_list)
        pfi = lint.get("per-file-ignores", {})
        per_file += len(pfi)
        if ignore_list or pfi:
            details.append(f"{pyproject}: ignore={len(ignore_list)}, per-file-ignores={len(pfi)}")
    triggered = ignores > 20 or per_file > 5
    return {
        "triggered": triggered,
        "evidence": "; ".join(details[:5]),
        "check_output": f"ruff ignore={ignores}, per-file-ignores={per_file}",
        "ruff_ignore_codes": ignores,
        "ruff_per_file_ignores": per_file,
        "observed_fact": f"ruff ignores {ignores} rule(s) across {per_file} file pattern(s).",
    }


_TODO_FIXME_RE = re.compile(r"TODO|FIXME|XXX|HACK", re.IGNORECASE)


def _check_todo_backlog(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    files = _py_files(repo_path) + _source_files(repo_path, {".js", ".ts", ".tsx", ".md"})
    total, snippets = _match_count(files, _TODO_FIXME_RE)
    return {
        "triggered": total > 50,
        "evidence": f"{total} occurrences; examples: " + "; ".join(snippets[:5]),
        "check_output": f"{total} TODO/FIXME/XXX/HACK comments",
        "todo_fixup_count": total,
        "todo_fixme_count": total,
        "observed_fact": f"{total} TODO/FIXME/XXX/HACK comment(s) remain in source.",
    }


def _check_contract_drift(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    openapi_dir = repo_path / "contracts" / "openapi"
    openapi_files = (
        list(openapi_dir.glob("*.yaml"))
        + list(openapi_dir.glob("*.yml"))
        + list(openapi_dir.glob("*.json"))
        if openapi_dir.exists()
        else []
    )
    route_dirs = (
        [p for p in (repo_path / "services").rglob("api/routes") if p.is_dir()]
        if (repo_path / "services").exists()
        else []
    )
    gap = max(0, len(route_dirs) - len(openapi_files))
    return {
        "triggered": gap > 0,
        "evidence": f"{len(openapi_files)} OpenAPI specs for {len(route_dirs)} route directories",
        "check_output": f"openapi_files={len(openapi_files)}, route_dirs={len(route_dirs)}",
        "openapi_files": len(openapi_files),
        "service_route_dirs": len(route_dirs),
        "contract_drift_gap": gap,
        "contract_drift_count": gap,
        "observed_fact": f"{gap} service route group(s) lack a matching OpenAPI contract file.",
    }


def _check_migration_downgrades(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    missing: list[str] = []
    services_dir = repo_path / "services"
    if not services_dir.exists():
        return {"triggered": False, "migration_files": 0, "migration_issue_count": 0}
    migration_files = [
        p
        for p in _walk_files(repo_path, roots=[services_dir], extensions={".py"})
        if "migrations/versions" in p.as_posix()
    ]
    for migration in migration_files:
        content = "\n".join(_read_lines(migration))
        if "def downgrade" not in content:
            missing.append(str(migration))
    return {
        "triggered": bool(missing),
        "evidence": "; ".join(missing[:10]),
        "check_output": f"{len(missing)} migrations missing downgrade",
        "migration_files": len(migration_files),
        "migration_issue_count": len(missing),
        "observed_fact": f"{len(missing)} Alembic migration file(s) are missing a downgrade function.",
    }


_PYDANTIC_V1_RE = re.compile(
    r"from\s+pydantic\.v1|__root__|orm_mode|Config\s*=",
)


def _check_pydantic_v1(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    total, snippets = _match_count(_py_files(repo_path), _PYDANTIC_V1_RE)
    return {
        "triggered": total > 0,
        "evidence": "; ".join(snippets[:10]),
        "check_output": f"{total} pydantic v1 or legacy config patterns",
        "pydantic_v1_hits": total,
        "observed_fact": f"{total} legacy pydantic v1 or ``Config`` pattern reference(s) found.",
    }


_ENV_ACCESS_RE = re.compile(r"os\.environ\[|os\.getenv\(")


def _check_unvalidated_env(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    files = [p for p in _py_files(repo_path) if "test" not in p.parts]
    total, snippets = _match_count(files, _ENV_ACCESS_RE)
    return {
        "triggered": total > 50,
        "evidence": f"{total} raw environment accesses; examples: " + "; ".join(snippets[:5]),
        "check_output": f"{total} os.environ/os.getenv accesses",
        "raw_env_access_count": total,
        "observed_fact": f"{total} raw environment variable access(es) without visible validation.",
    }


_IDEMPOTENCY_RE = re.compile(r"@router\.(post|put|patch)\(")


def _check_idempotency_gaps(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    route_files = [p for p in _py_files(repo_path) if "api/routes" in p.as_posix() or "api" in p.parts]
    non_idempotent = 0
    examples: list[str] = []
    for file_path in route_files:
        content = "\n".join(_read_lines(file_path))
        if "idempotency" in content.lower():
            continue
        matches = list(_IDEMPOTENCY_RE.finditer(content))
        if matches:
            non_idempotent += len(matches)
            if len(examples) < 5:
                examples.append(f"{file_path}:{matches[0].start()}")
    return {
        "triggered": non_idempotent > 0,
        "evidence": "; ".join(examples[:5]),
        "check_output": f"{non_idempotent} mutating endpoints without idempotency mention",
        "non_idempotent_endpoints": non_idempotent,
        "missing_idempotency_count": non_idempotent,
        "observed_fact": f"{non_idempotent} mutating endpoint(s) lack idempotency controls.",
    }


def _check_missing_unit_tests(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    services_dir = repo_path / "services"
    if not services_dir.exists():
        return {"triggered": False, "services_missing_unit_tests": 0}
    missing: list[str] = []
    for service in services_dir.iterdir():
        if not service.is_dir() or service.name.startswith("."):
            continue
        unit_dir = service / "tests" / "unit"
        has_tests = unit_dir.exists() and any(unit_dir.rglob("*.py"))
        if not has_tests:
            missing.append(service.name)
    return {
        "triggered": bool(missing),
        "evidence": "; ".join(missing[:10]),
        "check_output": f"{len(missing)} services missing unit tests",
        "services_missing_unit_tests": len(missing),
        "observed_fact": f"{len(missing)} service(s) do not have a populated ``tests/unit`` directory.",
    }


def _check_pytest_timeouts(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    configured = False
    for pyproject, _ in _pyproject_sections(repo_path, "pytest"):
        ini = pyproject
        data = _load_yaml(ini)
        if data and "timeout" in str(data.get("tool", {}).get("pytest", {}).get("ini_options", {})):
            configured = True
            break
    pytest_ini = repo_path / "pytest.ini"
    if pytest_ini.exists() and "timeout" in "\n".join(_read_lines(pytest_ini)):
        configured = True
    return {
        "triggered": not configured,
        "evidence": "No pytest timeout configuration found in pyproject.toml/pytest.ini",
        "check_output": f"pytest_timeout_configured={configured}",
        "pytest_timeout_configured": configured,
        "observed_fact": "pytest is not configured with a global timeout, risking hung CI jobs.",
    }


def _check_coverage_config(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    has_coverage = (repo_path / ".coveragerc").exists() or bool(
        _pyproject_sections(repo_path, "coverage")
    )
    return {
        "triggered": not has_coverage,
        "evidence": "No .coveragerc or [tool.coverage] section found",
        "check_output": f"coverage_configured={has_coverage}",
        "coverage_configured": has_coverage,
        "observed_fact": "No coverage configuration is present to enforce test coverage gates.",
    }


_SKIP_WITHOUT_REASON_RE = re.compile(
    r"@pytest\.mark\.skip\([^)]*\)(?!.*reason=)|pytest\.skip\([^)]*\)(?!.*reason=)",
)


def _check_test_skips(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    test_files = [
        p for p in _py_files(repo_path) if "test" in p.parts or p.name.startswith("test_")
    ]
    total, snippets = _match_count(test_files, _SKIP_WITHOUT_REASON_RE)
    return {
        "triggered": total > 0,
        "evidence": "; ".join(snippets[:10]),
        "check_output": f"{total} test skips without reason",
        "skips_without_reason": total,
        "observed_fact": f"{total} test skip(s) do not specify a reason, complicating triage.",
    }


def _check_parallel_tests(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    parallel = False
    for pyproject in _find_pyprojects(repo_path):
        data = _load_yaml(pyproject)
        if data:
            addopts = str(
                data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("addopts", "")
            )
            if "-n" in addopts:
                parallel = True
                break
    pytest_ini = repo_path / "pytest.ini"
    if pytest_ini.exists() and "-n" in "\n".join(_read_lines(pytest_ini)):
        parallel = True
    requirements = repo_path / "requirements.txt"
    if requirements.exists() and "pytest-xdist" in "\n".join(_read_lines(requirements)):
        parallel = True
    return {
        "triggered": not parallel,
        "evidence": "No pytest-xdist -n option detected in pytest configuration",
        "check_output": f"parallel_test_configured={parallel}",
        "parallel_test_configured": parallel,
        "no_parallel_tests": not parallel,
        "observed_fact": "Test suite is not configured for parallel execution, lengthening CI feedback.",
    }


_SECRET_RE = re.compile(
    r"(?i)(password|secret|token|api_key|apikey)\s*=\s*[\"'][^\"']{4,}[\"']",
)


def _check_hardcoded_secrets(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    files = [repo_path / ".env.example"] if (repo_path / ".env.example").exists() else []
    files += _py_files(repo_path)
    files = list({str(p): p for p in files}.values())
    total, snippets = _match_count(files, _SECRET_RE)
    return {
        "triggered": total > 0,
        "evidence": "; ".join(snippets[:10]),
        "check_output": f"{total} potential hardcoded secret patterns",
        "secret_pattern_hits": total,
        "observed_fact": f"{total} potential hardcoded secret or credential pattern(s) detected.",
    }


def _check_security_workflow(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    present = (repo_path / ".github" / "workflows" / "security-gates.yml").exists()
    return {
        "triggered": not present,
        "evidence": "Missing .github/workflows/security-gates.yml" if not present else "",
        "check_output": f"security_workflow_present={present}",
        "security_workflow_present": present,
        "observed_fact": "No dedicated security gates workflow is present in the repository.",
    }


def _check_dependency_pinning(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    package_json = repo_path / "package.json"
    unpinned = 0
    details: list[str] = []
    if package_json.exists():
        try:
            data = _load_yaml(package_json) or {}
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
            for name, version in deps.items():
                if isinstance(version, str) and (
                    version.startswith("^") or version.startswith("~")
                ):
                    unpinned += 1
                    if len(details) < 5:
                        details.append(f"{name}@{version}")
        except Exception:
            pass
    return {
        "triggered": unpinned > 10,
        "evidence": "; ".join(details[:5]),
        "check_output": f"{unpinned} unpinned npm dependencies",
        "unpinned_dependencies": unpinned,
        "observed_fact": f"{unpinned} npm dependency(ies) use caret/tilde ranges instead of exact pins.",
    }


_GUARDRAIL_RE = re.compile(r"do not|guardrail|policy|restrict|allowed", re.IGNORECASE)


def _check_llm_guardrails(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    prompts_dir = repo_path / ".agent" / "skills"
    if not prompts_dir.exists():
        return {"triggered": False, "prompts_missing_guardrails": 0}
    missing: list[str] = []
    for prompt in prompts_dir.rglob("*.txt"):
        content = "\n".join(_read_lines(prompt))
        if not _GUARDRAIL_RE.search(content):
            missing.append(str(prompt))
    return {
        "triggered": bool(missing),
        "evidence": "; ".join(missing[:5]),
        "check_output": f"{len(missing)} LLM prompts lack guardrail language",
        "prompts_missing_guardrails": len(missing),
        "missing_llm_guardrails": bool(missing),
        "observed_fact": f"{len(missing)} LLM prompt file(s) do not contain obvious guardrail language.",
    }


def _check_workflow_secrets(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    workflows_dir = repo_path / ".github" / "workflows"
    if not workflows_dir.exists():
        return {"triggered": False, "workflow_secret_references": 0}
    total = 0
    examples: list[str] = []
    secret_re = re.compile(r"secrets\.\w+|\$\{\{\s*secrets\.\w+\s*\}\}")
    for wf in workflows_dir.glob("*.yml"):
        count, snippets = _match_count([wf], secret_re)
        total += count
        examples.extend(snippets[:3])
    return {
        "triggered": total > 0,
        "evidence": "; ".join(examples[:10]),
        "check_output": f"{total} workflow secret references",
        "workflow_secret_references": total,
        "observed_fact": f"{total} workflow reference(s) to repository secrets were found.",
    }


def _check_ci_timeouts(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    workflows_dir = repo_path / ".github" / "workflows"
    if not workflows_dir.exists():
        return {"triggered": False, "ci_jobs_missing_timeouts": 0}
    missing = 0
    examples: list[str] = []
    for wf in workflows_dir.glob("*.yml"):
        try:
            data = _load_yaml(wf) or {}
        except Exception:
            continue
        jobs = data.get("jobs", {}) or {}
        for job_name, job in jobs.items():
            if isinstance(job, dict) and "timeout-minutes" not in job:
                missing += 1
                if len(examples) < 5:
                    examples.append(f"{wf.name}::{job_name}")
    return {
        "triggered": missing > 0,
        "evidence": "; ".join(examples[:10]),
        "check_output": f"{missing} CI jobs missing timeout-minutes",
        "ci_jobs_missing_timeouts": missing,
        "missing_ci_timeouts": missing > 0,
        "observed_fact": f"{missing} CI job(s) do not specify a ``timeout-minutes`` value.",
    }


def _check_pr_template(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    template = repo_path / ".github" / "pull_request_template.md"
    present = template.exists() and template.stat().st_size > 0
    return {
        "triggered": not present,
        "evidence": "Missing or empty .github/pull_request_template.md" if not present else "",
        "check_output": f"pr_template_present={present}",
        "pr_template_present": present,
        "observed_fact": "No pull request template exists to enforce governance checklists.",
    }


def _check_dependabot(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    present = (repo_path / ".github" / "dependabot.yml").exists()
    return {
        "triggered": not present,
        "evidence": "Missing .github/dependabot.yml" if not present else "",
        "check_output": f"dependabot_present={present}",
        "dependabot_present": present,
        "observed_fact": "Dependabot is not configured for automated dependency updates.",
    }


_HTTP_CALL_RE = re.compile(r"(?:requests|httpx)\.(get|post|put|patch|delete)\(")


def _check_http_timeouts(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    total = 0
    examples: list[str] = []
    for file_path in _py_files(repo_path):
        lines = _read_lines(file_path)
        for i, line in enumerate(lines, start=1):
            if _HTTP_CALL_RE.search(line) and "timeout=" not in line:
                total += 1
                if len(examples) < 8:
                    examples.append(f"{file_path}:{i}")
    return {
        "triggered": total > 0,
        "evidence": "; ".join(examples[:10]),
        "check_output": f"{total} HTTP calls missing explicit timeout",
        "http_calls_missing_timeout": total,
        "observed_fact": f"{total} HTTP client call(s) omit an explicit timeout.",
    }


def _check_health_endpoints(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    services_dir = repo_path / "services"
    if not services_dir.exists():
        return {"triggered": False, "services_missing_health": 0}
    missing: list[str] = []
    for service in services_dir.iterdir():
        if not service.is_dir():
            continue
        route_files = list(service.rglob("api/routes/*.py"))
        if not route_files:
            continue
        has_health = any("/health" in "\n".join(_read_lines(rf)) for rf in route_files)
        if not has_health:
            missing.append(service.name)
    return {
        "triggered": bool(missing),
        "evidence": "; ".join(missing[:10]),
        "check_output": f"{len(missing)} services missing /health endpoint",
        "services_missing_health": len(missing),
        "missing_health_checks": bool(missing),
        "observed_fact": f"{len(missing)} service(s) do not expose a ``/health`` endpoint.",
    }


def _check_stale_runbooks(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    runbook = repo_path / "RUNBOOK.md"
    if not runbook.exists():
        return {
            "triggered": True,
            "evidence": "RUNBOOK.md is missing from the repository root",
            "check_output": "runbook_present=false",
            "runbook_age_days": None,
            "observed_fact": "No RUNBOOK.md exists to guide incident response.",
        }
    mtime = datetime.fromtimestamp(runbook.stat().st_mtime, tz=UTC)
    age_days = (datetime.now(UTC) - mtime).days
    stale = age_days > 180
    return {
        "triggered": stale,
        "evidence": f"RUNBOOK.md last modified {age_days} days ago",
        "check_output": f"runbook_age_days={age_days}",
        "runbook_age_days": age_days,
        "stale_runbook_count": 1 if stale else 0,
        "observed_fact": f"RUNBOOK.md has not been updated in {age_days} days.",
    }


def _check_graceful_shutdown(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    files = [
        p
        for p in _py_files(repo_path)
        if p.name in {"main.py", "app.py", "lifespan.py", "server.py"}
    ]
    total = 0
    for file_path in files:
        content = "\n".join(_read_lines(file_path)).lower()
        if any(term in content for term in ("sigterm", "sigint", "atexit", "shutdown")):
            total += 1
    return {
        "triggered": total < 1,
        "evidence": "No signal/atexit shutdown handlers found in service entrypoints",
        "check_output": f"shutdown_handler_references={total}",
        "shutdown_handler_references": total,
        "no_graceful_shutdown": total < 1,
        "observed_fact": "Service entrypoints lack explicit graceful shutdown handlers.",
    }


_TIER1_DOCS = [
    "AGENTS.md",
    "README.md",
    "CONTRIBUTING.md",
    "TESTING.md",
    "SECURITY.md",
    "STATUS.md",
    "ROADMAP.md",
    "RUNBOOK.md",
    "CHANGELOG.md",
    "CODEOWNERS",
    "LICENSE",
]

_TIER2_DOCS = [
    "DESIGN.md",
    "DEVELOPMENT.md",
    "DEPLOYMENT.md",
    "OPERATIONS.md",
    "API.md",
    "DATA_MODEL.md",
    "DECISIONS.md",
    "THREAT_MODEL.md",
]


def _check_missing_tier1_docs(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    missing = [name for name in _TIER1_DOCS if not (repo_path / name).exists()]
    return {
        "triggered": bool(missing),
        "evidence": "; ".join(missing[:10]),
        "check_output": f"{len(missing)} missing tier-1 docs",
        "missing_tier1_docs": missing,
        "missing_root_doc_count": len(missing),
        "observed_fact": f"{len(missing)} expected tier-1 governance document(s) are missing.",
    }


def _check_missing_tier2_docs(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    missing = [name for name in _TIER2_DOCS if not (repo_path / name).exists()]
    return {
        "triggered": bool(missing),
        "evidence": "; ".join(missing[:10]),
        "check_output": f"{len(missing)} missing tier-2 docs",
        "missing_tier2_docs": missing,
        "observed_fact": f"{len(missing)} expected tier-2 governance document(s) are missing.",
    }


def _check_adr_gaps(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    adr_dir = repo_path / "docs" / "explanations" / "adr"
    if not adr_dir.exists():
        return {"triggered": False, "adr_gaps": []}
    numbers: list[int] = []
    for path in adr_dir.glob("ADR-*.md"):
        match = re.search(r"ADR-(\d+)", path.name)
        if match:
            numbers.append(int(match.group(1)))
    if not numbers:
        return {"triggered": False, "adr_gaps": [], "missing_adr_count": 0}
    numbers.sort()
    full_range = set(range(1, numbers[-1] + 1))
    gaps = sorted(full_range - set(numbers))
    return {
        "triggered": bool(gaps),
        "evidence": f"Missing ADR numbers: {gaps[:10]}",
        "check_output": f"adr_gaps={gaps}",
        "adr_gaps": gaps,
        "missing_adr_count": len(gaps),
        "observed_fact": f"{len(gaps)} gap(s) detected in ADR numbering sequence.",
    }


def _check_conflicting_claims(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    docs = [repo_path / "AGENTS.md", repo_path / "README.md", repo_path / "DESIGN.md"]
    docs = [p for p in docs if p.exists()]
    text = "\n".join("\n".join(_read_lines(p)) for p in docs).lower()
    npm = "npm install" in text or "npm ci" in text
    pnpm = "pnpm install" in text or "pnpm --dir" in text
    triggered = npm and pnpm
    return {
        "triggered": triggered,
        "evidence": (
            "Both npm and pnpm installation instructions appear in docs" if triggered else ""
        ),
        "check_output": f"npm_mentioned={npm}, pnpm_mentioned={pnpm}",
        "conflicting_claims": triggered,
        "conflicting_claim_count": 1 if triggered else 0,
        "observed_fact": "Documentation contains conflicting package manager guidance.",
    }


def _check_missing_repo_audit_skill(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    skill_dir = repo_path / ".agent" / "skills" / "repo-audit"
    present = (
        skill_dir.exists()
        and (skill_dir / "SKILL.md").exists()
        and (skill_dir / "config.yaml").exists()
    )
    return {
        "triggered": not present,
        "evidence": (
            "Missing .agent/skills/repo-audit/SKILL.md or config.yaml" if not present else ""
        ),
        "check_output": f"repo_audit_skill_present={present}",
        "repo_audit_skill_present": present,
        "missing_skill_definition_count": 0 if present else 1,
        "observed_fact": "The repo-audit skill package is missing or incomplete.",
    }


def _check_skill_prompts_complete(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    prompts_dir = repo_path / ".agent" / "skills" / "repo-audit" / "prompts"
    expected = {
        "system.txt",
        "analyze_git.txt",
        "analyze_code.txt",
        "analyze_docs.txt",
        "generate_report.txt",
    }
    if not prompts_dir.exists():
        return {
            "triggered": True,
            "evidence": "Missing .agent/skills/repo-audit/prompts directory",
            "check_output": "repo_audit_prompts_complete=false",
            "repo_audit_prompts_complete": False,
            "observed_fact": "The repo-audit skill is missing its prompt directory.",
        }
    present = {p.name for p in prompts_dir.glob("*.txt")}
    missing = sorted(expected - present)
    return {
        "triggered": bool(missing),
        "evidence": "; ".join(missing),
        "check_output": f"missing_prompts={missing}",
        "repo_audit_prompts_complete": not missing,
        "observed_fact": f"{len(missing)} expected repo-audit prompt file(s) are missing.",
    }


def _check_agents_md_audit_rules(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    agents_md = repo_path / "AGENTS.md"
    if not agents_md.exists():
        return {
            "triggered": True,
            "evidence": "AGENTS.md is missing",
            "check_output": "agents_md_present=false",
            "agents_md_mentions_audit": False,
            "observed_fact": "AGENTS.md is missing, so audit agent rules are not documented.",
        }
    content = "\n".join(_read_lines(agents_md)).lower()
    mentions = "audit" in content or "auditor" in content or "audit orchestrator" in content
    return {
        "triggered": not mentions,
        "evidence": "AGENTS.md does not reference the audit agent" if not mentions else "",
        "check_output": f"agents_md_mentions_audit={mentions}",
        "agents_md_mentions_audit": mentions,
        "observed_fact": "AGENTS.md does not mention the AuditOrchestrator or audit rules.",
    }


def _check_tool_schema_completeness(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    tools_dir = repo_path / ".agent" / "tools"
    if not tools_dir.exists():
        return {
            "triggered": True,
            "evidence": "Missing .agent/tools directory",
            "check_output": "tools_dir_present=false",
            "tools_with_missing_schema": 0,
            "observed_fact": "The .agent/tools directory is missing.",
        }
    tool_files = list(tools_dir.rglob("*.json"))
    if not tool_files:
        return {
            "triggered": True,
            "evidence": "No tool schema JSON files found under .agent/tools",
            "check_output": "tool_schema_files=0",
            "tools_with_missing_schema": 0,
            "observed_fact": "No tool schema files are present under .agent/tools.",
        }
    missing_schema = 0
    examples: list[str] = []
    for tool in tool_files:
        data = _load_yaml(tool)
        if not isinstance(data, dict) or not all(k in data for k in ("name", "description")):
            missing_schema += 1
            if len(examples) < 5:
                examples.append(str(tool))
    return {
        "triggered": missing_schema > 0,
        "evidence": "; ".join(examples[:5]),
        "check_output": f"{missing_schema} tools with incomplete schema",
        "tools_with_missing_schema": missing_schema,
        "unconfigured_tool_count": missing_schema,
        "observed_fact": f"{missing_schema} tool schema file(s) are missing required fields.",
    }


def _check_missing_debug_config(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    present = (repo_path / ".vscode" / "launch.json").exists() or bool(
        _pyproject_sections(repo_path, "debugpy")
    )
    return {
        "triggered": not present,
        "evidence": "No .vscode/launch.json or debugpy config found",
        "check_output": f"debug_config_present={present}",
        "debug_config_present": present,
        "missing_debug_config": not present,
        "observed_fact": "No IDE debug configuration is present for local development.",
    }


def _check_infisical_barrier(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    agents_md = repo_path / "AGENTS.md"
    if not agents_md.exists():
        return {
            "triggered": False,
            "evidence": "AGENTS.md missing; cannot evaluate onboarding",
            "check_output": "agents_md_present=false",
            "infisical_fallback_present": False,
            "observed_fact": "AGENTS.md is missing; onboarding path cannot be evaluated.",
        }
    content = "\n".join(_read_lines(agents_md)).lower()
    mentions_infisical = "infisical" in content
    mentions_fallback = "cp .env.example" in content or ".env.example" in content
    triggered = mentions_infisical and not mentions_fallback
    return {
        "triggered": triggered,
        "evidence": (
            "AGENTS.md requires Infisical without documenting .env.example fallback"
            if triggered
            else ""
        ),
        "check_output": f"mentions_infisical={mentions_infisical}, mentions_fallback={mentions_fallback}",
        "infisical_fallback_present": not triggered,
        "secret_management_barrier": triggered,
        "observed_fact": "Onboarding documentation mandates Infisical without a documented env fallback.",
    }


def _check_fast_unit_marker(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    has_unit_marker = False
    for pyproject in _find_pyprojects(repo_path):
        data = _load_yaml(pyproject)
        if data:
            markers = (
                data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("markers", [])
            )
            if any("unit" in str(m) for m in markers):
                has_unit_marker = True
                break
    pytest_ini = repo_path / "pytest.ini"
    if pytest_ini.exists() and "unit" in "\n".join(_read_lines(pytest_ini)):
        has_unit_marker = True
    return {
        "triggered": not has_unit_marker,
        "evidence": "No 'unit' pytest marker configured for fast tests",
        "check_output": f"fast_unit_marker_present={has_unit_marker}",
        "fast_unit_marker_present": has_unit_marker,
        "observed_fact": "No dedicated ``unit`` pytest marker exists for fast, isolated tests.",
    }


# ---------------------------------------------------------------------------
# Catalog definition
# ---------------------------------------------------------------------------

SEED_FINDINGS: list[dict[str, Any]] = [
    # Architecture
    {
        "id": "ARCH-001",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "area": AuditArea.ARCHITECTURE,
        "effort": "L",
        "risk_of_change": "Medium",
        "owner": "Platform Architecture",
        "target_sprint": 1,
        "observed_fact": "Python modules exceed the recommended maximum line count.",
        "inference_risk": "Oversized modules concentrate complexity and slow reviews and testing.",
        "business_impact": "Slower delivery velocity and higher defect escape rate.",
        "recommended_fix": "Refactor large modules into smaller, single-responsibility modules.",
        "check": _check_oversized_python,
    },
    {
        "id": "ARCH-002",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.ARCHITECTURE,
        "effort": "M",
        "risk_of_change": "Low",
        "owner": "Frontend Platform",
        "target_sprint": 2,
        "observed_fact": "Frontend source files exceed the recommended line count.",
        "inference_risk": "Large components become difficult to test, compose, and reason about.",
        "business_impact": "UI changes take longer and regressions become more likely.",
        "recommended_fix": "Split large components and utility files by concern.",
        "check": _check_oversized_frontend,
    },
    {
        "id": "ARCH-003",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.ARCHITECTURE,
        "effort": "M",
        "risk_of_change": "Low",
        "owner": "Platform Architecture",
        "target_sprint": 2,
        "observed_fact": "Duplicate source files were detected by content hash.",
        "inference_risk": "Duplicate code increases maintenance burden and drift risk.",
        "business_impact": "Bug fixes must be applied in multiple places, risking inconsistency.",
        "recommended_fix": "Deduplicate into shared packages or utilities.",
        "check": _check_duplicate_files,
    },
    {
        "id": "ARCH-004",
        "severity": Severity.LOW,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.ARCHITECTURE,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Platform Architecture",
        "target_sprint": 3,
        "observed_fact": "Source files are nested deeper than eight directory levels.",
        "inference_risk": "Deep nesting signals poor package cohesion and discovery friction.",
        "business_impact": "New contributors struggle to locate relevant code.",
        "recommended_fix": "Flatten overly deep package trees and restructure by domain.",
        "check": _check_deep_nesting,
    },
    {
        "id": "ARCH-005",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.ARCHITECTURE,
        "effort": "L",
        "risk_of_change": "High",
        "owner": "Platform Architecture",
        "target_sprint": 1,
        "observed_fact": "Cross-layer imports violate the six-layer boundary policy.",
        "inference_risk": "Layer coupling undermines modularity and independent deployability.",
        "business_impact": "Changes in one layer can unexpectedly cascade into others.",
        "recommended_fix": "Route cross-layer calls through the API gateway or shared packages.",
        "check": _check_service_boundaries,
    },
    # Code Quality
    {
        "id": "CQ-001",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.CODE_QUALITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Backend Guild",
        "target_sprint": 2,
        "observed_fact": "Relative imports are used extensively in Python packages.",
        "inference_risk": "Relative imports make refactoring and package relocation fragile.",
        "business_impact": "Renaming or moving packages creates churn and import errors.",
        "recommended_fix": "Convert relative imports to absolute canonical imports.",
        "check": _check_relative_imports,
    },
    {
        "id": "CQ-002",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "area": AuditArea.CODE_QUALITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Backend Guild",
        "target_sprint": 1,
        "observed_fact": "Bare ``except:`` clauses catch all exceptions indiscriminately.",
        "inference_risk": "Bare excepts hide programming errors and break error handling contracts.",
        "business_impact": "Bugs become harder to diagnose and may be silently swallowed.",
        "recommended_fix": "Replace bare excepts with specific exception types.",
        "check": _check_bare_excepts,
    },
    {
        "id": "CQ-003",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.CODE_QUALITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Backend Guild",
        "target_sprint": 2,
        "observed_fact": "mypy configuration disables strictness checks.",
        "inference_risk": "Disabled type checks allow type errors to reach production.",
        "business_impact": "Runtime type failures increase support load and incident frequency.",
        "recommended_fix": "Remove non-essential mypy overrides and address root causes.",
        "check": _check_mypy_disabled,
    },
    {
        "id": "CQ-004",
        "severity": Severity.LOW,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.CODE_QUALITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Backend Guild",
        "target_sprint": 3,
        "observed_fact": "ruff is configured to ignore a large number of lint rules.",
        "inference_risk": "Broad lint overrides hide maintainability and correctness issues.",
        "business_impact": "Technical debt accumulates faster than the linter can surface it.",
        "recommended_fix": "Tighten ruff ignore lists and resolve underlying issues incrementally.",
        "check": _check_ruff_sprawl,
    },
    {
        "id": "CQ-005",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.CODE_QUALITY,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Backend Guild",
        "target_sprint": 4,
        "observed_fact": "A large backlog of TODO/FIXME/XXX/HACK comments remains in source.",
        "inference_risk": "Comment debt often signals deferred defects and design shortcuts.",
        "business_impact": "Known issues are forgotten until they surface in production.",
        "recommended_fix": "Convert actionable comments into tracked tickets and resolve them.",
        "check": _check_todo_backlog,
    },
    # Correctness
    {
        "id": "COR-001",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.CORRECTNESS,
        "effort": "M",
        "risk_of_change": "Medium",
        "owner": "API Platform",
        "target_sprint": 1,
        "observed_fact": "OpenAPI contracts are not aligned with the number of service route groups.",
        "inference_risk": "Undocumented or mismatched contracts cause integration drift.",
        "business_impact": "Consumers break when route behavior changes without contract updates.",
        "recommended_fix": "Add or update OpenAPI specs for every route group and gate drift in CI.",
        "check": _check_contract_drift,
    },
    {
        "id": "COR-002",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.CORRECTNESS,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Data Platform",
        "target_sprint": 2,
        "observed_fact": "Alembic migrations are missing downgrade functions.",
        "inference_risk": "Missing downgrades prevent safe rollback during failed deployments.",
        "business_impact": "Production incidents may require manual, error-prone recovery.",
        "recommended_fix": "Add downgrade functions to every migration or document exceptions.",
        "check": _check_migration_downgrades,
    },
    {
        "id": "COR-003",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.CORRECTNESS,
        "effort": "M",
        "risk_of_change": "Medium",
        "owner": "Backend Guild",
        "target_sprint": 2,
        "observed_fact": "Legacy pydantic v1 or ``Config`` patterns remain in the codebase.",
        "inference_risk": "Legacy patterns may be deprecated or incompatible with future upgrades.",
        "business_impact": "Upgrade paths become blocked, increasing migration cost.",
        "recommended_fix": "Migrate to pydantic v2 idioms and remove legacy config classes.",
        "check": _check_pydantic_v1,
    },
    {
        "id": "COR-004",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.CORRECTNESS,
        "effort": "M",
        "risk_of_change": "Medium",
        "owner": "Backend Guild",
        "target_sprint": 2,
        "observed_fact": "Environment variables are read directly without visible validation.",
        "inference_risk": "Missing validation leads to misconfiguration and runtime failures.",
        "business_impact": "Services may start with invalid config and fail silently or loudly.",
        "recommended_fix": "Centralize environment parsing through validated config models.",
        "check": _check_unvalidated_env,
    },
    {
        "id": "COR-005",
        "severity": Severity.HIGH,
        "confidence": Confidence.LOW,
        "area": AuditArea.CORRECTNESS,
        "effort": "L",
        "risk_of_change": "Medium",
        "owner": "API Platform",
        "target_sprint": 1,
        "observed_fact": "Mutating API endpoints do not mention idempotency controls.",
        "inference_risk": "Retry storms and partial failures can create duplicate side effects.",
        "business_impact": "Data corruption and inconsistent state can result from retries.",
        "recommended_fix": "Add idempotency keys to POST/PUT/PATCH endpoints and document behavior.",
        "check": _check_idempotency_gaps,
    },
    # Testing
    {
        "id": "TEST-001",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "area": AuditArea.TESTING,
        "effort": "L",
        "risk_of_change": "Low",
        "owner": "Quality Engineering",
        "target_sprint": 1,
        "observed_fact": "Some services lack a populated ``tests/unit`` directory.",
        "inference_risk": "Untested services accumulate regression risk and slow refactoring.",
        "business_impact": "Production defects slip through because behavior is not verified.",
        "recommended_fix": "Add focused unit tests for every service entrypoint and pure function.",
        "check": _check_missing_unit_tests,
    },
    {
        "id": "TEST-002",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.TESTING,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Quality Engineering",
        "target_sprint": 2,
        "observed_fact": "pytest is not configured with a global timeout.",
        "inference_risk": "Hung tests can block CI pipelines indefinitely.",
        "business_impact": "Delayed feedback and wasted CI minutes reduce team velocity.",
        "recommended_fix": "Add pytest-timeout and a sensible default timeout to pytest options.",
        "check": _check_pytest_timeouts,
    },
    {
        "id": "TEST-003",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.TESTING,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Quality Engineering",
        "target_sprint": 2,
        "observed_fact": "No code coverage configuration is present.",
        "inference_risk": "Without coverage gating, untested code can merge unchecked.",
        "business_impact": "Regression risk grows as coverage gaps are not visible.",
        "recommended_fix": "Add coverage configuration and a CI gate for minimum coverage.",
        "check": _check_coverage_config,
    },
    {
        "id": "TEST-004",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.TESTING,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Quality Engineering",
        "target_sprint": 4,
        "observed_fact": "Test skips are used without a documented reason.",
        "inference_risk": "Unexplained skips hide broken or obsolete tests.",
        "business_impact": "Coverage gaps are not transparent and may mask regressions.",
        "recommended_fix": "Add a ``reason=`` to every pytest skip and review skipped tests.",
        "check": _check_test_skips,
    },
    {
        "id": "TEST-005",
        "severity": Severity.LOW,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.TESTING,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Quality Engineering",
        "target_sprint": 3,
        "observed_fact": "Test suite is not configured to run in parallel.",
        "inference_risk": "Sequential tests extend CI feedback loops and underutilize agents.",
        "business_impact": "Slower builds reduce developer iteration speed.",
        "recommended_fix": "Configure pytest-xdist and run tests with ``-n auto`` in CI.",
        "check": _check_parallel_tests,
    },
    # Security
    {
        "id": "SEC-001",
        "severity": Severity.CRITICAL,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.SECURITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Security",
        "target_sprint": 1,
        "observed_fact": "Potential hardcoded secrets or credential patterns were detected.",
        "inference_risk": "Committed credentials can be leaked and abused by attackers.",
        "business_impact": "Data breaches, unauthorized access, and compliance violations.",
        "recommended_fix": "Move secrets to a vault, rotate any exposed values, and add secret scanning.",
        "check": _check_hardcoded_secrets,
    },
    {
        "id": "SEC-002",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "area": AuditArea.SECURITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Security",
        "target_sprint": 1,
        "observed_fact": "No dedicated security gates workflow is present.",
        "inference_risk": "Vulnerabilities and supply-chain risks are not blocked at merge time.",
        "business_impact": "Security issues reach production before detection.",
        "recommended_fix": "Add a security-gates workflow with dependency and secret scanning.",
        "check": _check_security_workflow,
    },
    {
        "id": "SEC-003",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.SECURITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Security",
        "target_sprint": 2,
        "observed_fact": "Many npm dependencies use caret or tilde version ranges.",
        "inference_risk": "Loose ranges allow unexpected package updates and supply-chain drift.",
        "business_impact": "A compromised upstream package can be pulled automatically.",
        "recommended_fix": "Pin dependency versions and use lockfile integrity checks.",
        "check": _check_dependency_pinning,
    },
    {
        "id": "SEC-004",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.LOW,
        "area": AuditArea.SECURITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Security",
        "target_sprint": 2,
        "observed_fact": "LLM prompt files do not contain obvious guardrail language.",
        "inference_risk": "Prompts without guardrails may be susceptible to injection or misuse.",
        "business_impact": "Agents could produce harmful, incorrect, or out-of-policy outputs.",
        "recommended_fix": "Add explicit guardrail and policy language to every LLM prompt.",
        "check": _check_llm_guardrails,
    },
    {
        "id": "SEC-005",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.SECURITY,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Security",
        "target_sprint": 3,
        "observed_fact": "Workflows reference repository secrets directly.",
        "inference_risk": "Broad secret usage increases blast radius if a workflow is compromised.",
        "business_impact": "Leaked workflows could expose production credentials.",
        "recommended_fix": "Scope secrets to the jobs that need them and audit usage regularly.",
        "check": _check_workflow_secrets,
    },
    # CI/CD
    {
        "id": "CICD-001",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.CICD,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Platform Engineering",
        "target_sprint": 2,
        "observed_fact": "CI workflow jobs do not specify ``timeout-minutes``.",
        "inference_risk": "Jobs can hang indefinitely, blocking pipelines and consuming minutes.",
        "business_impact": "Longer incident recovery and inflated CI costs.",
        "recommended_fix": "Add ``timeout-minutes`` to every CI job.",
        "check": _check_ci_timeouts,
    },
    {
        "id": "CICD-002",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.CICD,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Platform Engineering",
        "target_sprint": 3,
        "observed_fact": "No pull request template is present.",
        "inference_risk": "PRs may omit governance, security, and testing context.",
        "business_impact": "Lower review quality and inconsistent merge standards.",
        "recommended_fix": "Add a PR template with required governance checklists.",
        "check": _check_pr_template,
    },
    {
        "id": "CICD-003",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.CICD,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Platform Engineering",
        "target_sprint": 3,
        "observed_fact": "Workflows directly consume repository secrets.",
        "inference_risk": "Direct secret use complicates rotation and auditability.",
        "business_impact": "Increased exposure if a workflow or action is compromised.",
        "recommended_fix": "Pass secrets via environments and limit workflow permissions.",
        "check": _check_workflow_secrets,
    },
    {
        "id": "CICD-004",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.CICD,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Platform Engineering",
        "target_sprint": 4,
        "observed_fact": "Dependabot is not configured for the repository.",
        "inference_risk": "Vulnerable dependencies are not discovered automatically.",
        "business_impact": "Known CVEs remain in production until manual review.",
        "recommended_fix": "Add a .github/dependabot.yml for Python and npm ecosystems.",
        "check": _check_dependabot,
    },
    # Reliability
    {
        "id": "REL-001",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.RELIABILITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "SRE",
        "target_sprint": 2,
        "observed_fact": "HTTP client calls omit explicit timeouts.",
        "inference_risk": "Calls can hang forever, exhausting workers and cascading failures.",
        "business_impact": "Outages propagate when downstream dependencies degrade.",
        "recommended_fix": "Add explicit timeouts to every external HTTP call.",
        "check": _check_http_timeouts,
    },
    {
        "id": "REL-002",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.RELIABILITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "SRE",
        "target_sprint": 2,
        "observed_fact": "Some services do not expose a ``/health`` endpoint.",
        "inference_risk": "Load balancers and orchestrators cannot detect unhealthy instances.",
        "business_impact": "Failed instances may continue to receive traffic.",
        "recommended_fix": "Add a lightweight health endpoint to every service.",
        "check": _check_health_endpoints,
    },
    {
        "id": "REL-003",
        "severity": Severity.LOW,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.RELIABILITY,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "SRE",
        "target_sprint": 4,
        "observed_fact": "RUNBOOK.md is missing or has not been updated recently.",
        "inference_risk": "Outdated runbooks slow incident response and increase recovery time.",
        "business_impact": "Longer outages and higher operational stress during incidents.",
        "recommended_fix": "Create or refresh RUNBOOK.md with current procedures.",
        "check": _check_stale_runbooks,
    },
    {
        "id": "REL-004",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.RELIABILITY,
        "effort": "S",
        "risk_of_change": "Medium",
        "owner": "SRE",
        "target_sprint": 2,
        "observed_fact": "Service entrypoints lack explicit graceful shutdown handlers.",
        "inference_risk": "In-flight requests may be dropped during deploys or restarts.",
        "business_impact": "User-facing errors and data inconsistency during rollouts.",
        "recommended_fix": "Register SIGTERM/SIGINT handlers and drain in-flight work.",
        "check": _check_graceful_shutdown,
    },
    # Documentation
    {
        "id": "DOC-001",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.DOCUMENTATION,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Developer Experience",
        "target_sprint": 3,
        "observed_fact": "Expected tier-1 governance documents are missing from the repository root.",
        "inference_risk": "Contributors lack authoritative guidance on process, security, and operations.",
        "business_impact": "Onboarding friction and inconsistent engineering practices.",
        "recommended_fix": "Add the missing root-level governance documents.",
        "check": _check_missing_tier1_docs,
    },
    {
        "id": "DOC-002",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.DOCUMENTATION,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Developer Experience",
        "target_sprint": 4,
        "observed_fact": "Expected tier-2 technical reference documents are missing.",
        "inference_risk": "Deep technical context is tribal knowledge rather than documented.",
        "business_impact": "Harder maintenance, slower incident response, and knowledge silos.",
        "recommended_fix": "Add missing reference docs for architecture, data model, and operations.",
        "check": _check_missing_tier2_docs,
    },
    {
        "id": "DOC-003",
        "severity": Severity.LOW,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.DOCUMENTATION,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Developer Experience",
        "target_sprint": 4,
        "observed_fact": "ADR numbering contains gaps in the expected sequence.",
        "inference_risk": "Missing ADRs suggest undocumented or reversed decisions.",
        "business_impact": "Decision history is incomplete, complicating audits and onboarding.",
        "recommended_fix": "Backfill missing ADRs or renumber to maintain a contiguous sequence.",
        "check": _check_adr_gaps,
    },
    {
        "id": "DOC-004",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.DOCUMENTATION,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Developer Experience",
        "target_sprint": 3,
        "observed_fact": "Documentation contains conflicting package manager guidance.",
        "inference_risk": "Conflicting instructions lead to inconsistent local setups and lockfile drift.",
        "business_impact": "New contributors hit setup issues and CI may use the wrong package manager.",
        "recommended_fix": "Standardize on pnpm everywhere and remove npm references.",
        "check": _check_conflicting_claims,
    },
    # Agent Readiness
    {
        "id": "AGENT-001",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "area": AuditArea.AGENT_READINESS,
        "effort": "M",
        "risk_of_change": "Low",
        "owner": "Agent Platform",
        "target_sprint": 1,
        "observed_fact": "The ``repo-audit`` skill package is missing or incomplete.",
        "inference_risk": "The audit agent cannot be invoked as a portable skill by the agent harness.",
        "business_impact": "Audit capability is not reusable across workspaces and interfaces.",
        "recommended_fix": "Create .agent/skills/repo-audit with SKILL.md, config.yaml, and prompts.",
        "check": _check_missing_repo_audit_skill,
    },
    {
        "id": "AGENT-002",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "area": AuditArea.AGENT_READINESS,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Agent Platform",
        "target_sprint": 2,
        "observed_fact": "The ``repo-audit`` skill is missing expected prompt files.",
        "inference_risk": "LLM-powered phases of the audit agent cannot use consistent prompts.",
        "business_impact": "Agent output quality varies and is harder to govern.",
        "recommended_fix": "Add all required prompt files under .agent/skills/repo-audit/prompts.",
        "check": _check_skill_prompts_complete,
    },
    {
        "id": "AGENT-003",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.AGENT_READINESS,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Agent Platform",
        "target_sprint": 3,
        "observed_fact": "AGENTS.md does not reference the AuditOrchestrator or audit rules.",
        "inference_risk": "Agent fleet behavior is not documented or enforced for audit runs.",
        "business_impact": "Inconsistent agent behavior and missed governance checkpoints.",
        "recommended_fix": "Add audit agent triggers and rules to AGENTS.md.",
        "check": _check_agents_md_audit_rules,
    },
    {
        "id": "AGENT-004",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.AGENT_READINESS,
        "effort": "S",
        "risk_of_change": "Low",
        "owner": "Agent Platform",
        "target_sprint": 2,
        "observed_fact": "Tool schema files under .agent/tools are missing required fields.",
        "inference_risk": "The harness may reject tools or render them incorrectly.",
        "business_impact": "Agent capabilities are unavailable or behave unexpectedly.",
        "recommended_fix": "Validate every tool JSON against the required schema.",
        "check": _check_tool_schema_completeness,
    },
    # Dev Experience
    {
        "id": "DX-001",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.DEV_EXPERIENCE,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Developer Experience",
        "target_sprint": 4,
        "observed_fact": "No IDE debug configuration is present for the repository.",
        "inference_risk": "Developers must manually configure debugging, slowing troubleshooting.",
        "business_impact": "Longer debugging sessions and reduced developer productivity.",
        "recommended_fix": "Add a .vscode/launch.json or documented debugpy setup.",
        "check": _check_missing_debug_config,
    },
    {
        "id": "DX-002",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "area": AuditArea.DEV_EXPERIENCE,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Developer Experience",
        "target_sprint": 3,
        "observed_fact": "Onboarding instructions depend on Infisical without a documented env fallback.",
        "inference_risk": "Contributors who cannot access Infisical cannot start the stack.",
        "business_impact": "Higher barrier to contribution and onboarding delays.",
        "recommended_fix": "Document a manual ``.env.example`` fallback path in AGENTS.md.",
        "check": _check_infisical_barrier,
    },
    {
        "id": "DX-003",
        "severity": Severity.LOW,
        "confidence": Confidence.HIGH,
        "area": AuditArea.DEV_EXPERIENCE,
        "effort": "XS",
        "risk_of_change": "Low",
        "owner": "Developer Experience",
        "target_sprint": 4,
        "observed_fact": "No ``unit`` pytest marker is configured for fast tests.",
        "inference_risk": "Developers cannot run a quick, isolated subset of tests locally.",
        "business_impact": "Slower local validation and wider CI feedback loops.",
        "recommended_fix": "Register a ``unit`` marker and provide a Makefile target for fast tests.",
        "check": _check_fast_unit_marker,
    },
]


class FindingCatalog:
    """Pre-seeded catalog of audit findings with a lightweight check runner."""

    entries: list[dict[str, Any]] = SEED_FINDINGS

    @classmethod
    def check_all(
        cls,
        repo_path: str,
        config: AuditConfig,
        areas: list[AuditArea] | None = None,
    ) -> tuple[list[Finding], dict[str, Any]]:
        """Run every catalog check and return triggered findings plus metrics.

        Args:
            repo_path: Filesystem path to the repository root.
            config: Audit configuration.
            areas: Optional subset of areas to restrict checks to.

        Returns:
            Tuple of ``(findings, metrics)``.
        """
        path = Path(repo_path).resolve()
        findings: list[Finding] = []
        metrics: dict[str, Any] = {
            "checks_run": 0,
            "checks_triggered": 0,
            "findings_count": 0,
            "findings_by_area": {},
            "areas_enabled": [a.value for a in (areas or list(AuditArea))],
        }

        entries = [entry for entry in cls.entries if areas is None or entry["area"] in areas]
        for entry in entries:
            metrics["checks_run"] += 1
            result = entry["check"](path, config)

            # Merge non-narrative keys into metrics.
            for key, value in result.items():
                if key not in {
                    "triggered",
                    "evidence",
                    "observed_fact",
                    "inference_risk",
                    "business_impact",
                    "recommended_fix",
                    "check_output",
                }:
                    metrics.setdefault(key, value)

            if not result.get("triggered"):
                continue

            metrics["checks_triggered"] += 1
            finding = cls._build_finding(entry, result, config)
            findings.append(finding)

        metrics["findings_count"] = len(findings)
        metrics["findings_by_area"] = {
            area.value: sum(1 for f in findings if f.area == area)
            for area in (areas or list(AuditArea))
        }
        return findings, metrics

    @classmethod
    def _build_finding(
        cls,
        entry: dict[str, Any],
        result: dict[str, Any],
        config: AuditConfig,
    ) -> Finding:
        """Create a :class:`Finding` from a catalog entry and check result."""
        return Finding(
            id=entry["id"],
            severity=entry["severity"],
            confidence=entry["confidence"],
            area=entry["area"],
            evidence=result.get("evidence") or entry.get("evidence", ""),
            observed_fact=result.get("observed_fact") or entry["observed_fact"],
            inference_risk=entry["inference_risk"],
            business_impact=entry["business_impact"],
            recommended_fix=entry["recommended_fix"],
            effort=entry["effort"],
            risk_of_change=entry["risk_of_change"],
            owner=entry["owner"],
            target_sprint=entry.get("target_sprint", 0),
            analyzer_type="catalog",
            check_command=entry["check"].__name__,
            check_output=result.get("check_output"),
        )
