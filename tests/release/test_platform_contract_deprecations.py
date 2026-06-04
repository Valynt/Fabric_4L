from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import fnmatch
import json
from pathlib import Path
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_ROOTS = ("value_fabric", "services", "apps/web")
EXCLUDED_DIR_NAMES = {"docs", "examples", "example", "node_modules", ".git", ".venv", "venv", "dist", "build", "__pycache__"}
EXCEPTIONS_REGISTER = REPO_ROOT / "docs" / "governance" / "deprecations.json"


@dataclass(frozen=True)
class DeprecationRule:
    rule_id: str
    deprecated_pattern: str
    canonical_replacement: str
    replacement_module_path: str
    deadline: date
    file_globs: tuple[str, ...]


HIGH_RISK_RULES: tuple[DeprecationRule, ...] = (
    DeprecationRule(
        rule_id="PCD-001",
        deprecated_pattern="request.state.context",
        canonical_replacement="request.state.governance_context",
        replacement_module_path="value_fabric/shared/identity/",
        deadline=date(2026, 5, 15),
        file_globs=("*.py",),
    ),
    DeprecationRule(
        rule_id="PCD-002",
        deprecated_pattern="get_db_with_tenant(",
        canonical_replacement="get_db_from_context()",
        replacement_module_path="value_fabric/shared/db/",
        deadline=date(2026, 6, 1),
        file_globs=("*.py",),
    ),
    DeprecationRule(
        rule_id="PCD-003",
        deprecated_pattern="datetime.utcnow()",
        canonical_replacement="datetime.now(timezone.utc)",
        replacement_module_path="value_fabric/ and services/ Python runtime modules",
        deadline=date(2026, 6, 1),
        file_globs=("*.py",),
    ),
    DeprecationRule(
        rule_id="PCD-004",
        deprecated_pattern="window.location.href",
        canonical_replacement="useLocation from wouter",
        replacement_module_path="apps/web/src/ routing components",
        deadline=date(2026, 5, 15),
        file_globs=("*.ts", "*.tsx", "*.js", "*.jsx"),
    ),
)


def _iter_target_files() -> list[Path]:
    files: list[Path] = []
    result = subprocess.run(
        ["git", "ls-files", *CANONICAL_ROOTS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"Could not enumerate tracked runtime files: {result.stderr}")

    for raw_path in result.stdout.splitlines():
        path = REPO_ROOT / raw_path
        if not path.is_file():
            continue
        if set(path.parts).intersection(EXCLUDED_DIR_NAMES):
            continue
        files.append(path)
    return files


def _match_file(path: Path, globs: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path.name, pat) for pat in globs)


def _exception_ids_for_rule(rule_id: str) -> set[str]:
    if not EXCEPTIONS_REGISTER.exists():
        return set()

    payload = json.loads(EXCEPTIONS_REGISTER.read_text(encoding="utf-8"))
    exceptions = payload.get("exceptions", [])
    allowed: set[str] = set()

    for entry in exceptions:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", "")).strip()
        if not entry_id:
            continue
        targets = entry.get("appliesTo", [])
        if isinstance(targets, str):
            targets = [targets]
        if rule_id in targets and str(entry.get("status", "")).lower() in {"approved", "active"}:
            allowed.add(entry_id)
    return allowed


def _find_hits(rule: DeprecationRule) -> list[Path]:
    hits: list[Path] = []
    for path in _iter_target_files():
        if not _match_file(path, rule.file_globs):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if rule.deprecated_pattern in text:
            hits.append(path.relative_to(REPO_ROOT))
    return hits


@pytest.mark.release
@pytest.mark.parametrize("rule", HIGH_RISK_RULES, ids=lambda rule: rule.rule_id)
def test_high_risk_deprecations_enforced_after_deadline(rule: DeprecationRule) -> None:
    if date.today() < rule.deadline:
        # Deprecation deadline has not been reached yet; test is a no-op until then
        return

    hits = _find_hits(rule)
    if not hits:
        return

    allowed_exception_ids = _exception_ids_for_rule(rule.rule_id)
    if allowed_exception_ids:
        # Approved exceptions exist - skip this check
        return

    exception_message = (
        "No approved exception IDs found in docs/governance/deprecations.json under exceptions[]. "
        "Add an exception with appliesTo including the rule ID if temporary waiver is required."
    )

    formatted_hits = "\n".join(f"  - {path}" for path in hits[:20])
    more = "" if len(hits) <= 20 else f"\n  ... and {len(hits) - 20} more"

    pytest.fail(
        f"[Release Gate] Deprecated pattern remains past deadline for {rule.rule_id}.\n"
        f"Pattern: {rule.deprecated_pattern}\n"
        f"Deadline: {rule.deadline.isoformat()}\n"
        f"Use replacement: {rule.canonical_replacement}\n"
        f"Canonical module path: {rule.replacement_module_path}\n"
        f"Found in canonical runtime paths (value_fabric/, services/, apps/web/):\n{formatted_hits}{more}\n"
        f"{exception_message}"
    )
