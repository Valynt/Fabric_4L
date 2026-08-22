"""Catalog of deterministic findings and check runner.

Decomposed into cohesive submodules:
- ``catalog_helpers``: File system traversal, file reading, and config parsing helpers.
- ``catalog_checks``: Individual deterministic check functions and detection patterns.
- ``catalog_definitions``: Seed finding catalog definition metadata table.
- ``finding_catalog``: Main coordinator and backwards-compatible export facade.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

from ..models import AuditArea, AuditConfig, Confidence, Finding, Severity
from . import catalog_checks, catalog_definitions, catalog_helpers
from .catalog_checks import (
    _BARE_EXCEPT_RE,
    _CROSS_LAYER_RE,
    _ENV_ACCESS_RE,
    _GUARDRAIL_RE,
    _HTTP_CALL_RE,
    _IDEMPOTENCY_RE,
    _PYDANTIC_V1_RE,
    _RELATIVE_IMPORT_RE,
    _SECRET_RE,
    _SKIP_WITHOUT_REASON_RE,
    _TIER1_DOCS,
    _TIER2_DOCS,
    _TODO_FIXME_RE,
    _check_adr_gaps,
    _check_agents_md_audit_rules,
    _check_bare_excepts,
    _check_ci_timeouts,
    _check_conflicting_claims,
    _check_contract_drift,
    _check_coverage_config,
    _check_deep_nesting,
    _check_dependabot,
    _check_dependency_pinning,
    _check_duplicate_files,
    _check_fast_unit_marker,
    _check_graceful_shutdown,
    _check_hardcoded_secrets,
    _check_health_endpoints,
    _check_http_timeouts,
    _check_idempotency_gaps,
    _check_infisical_barrier,
    _check_llm_guardrails,
    _check_migration_downgrades,
    _check_missing_debug_config,
    _check_missing_repo_audit_skill,
    _check_missing_tier1_docs,
    _check_missing_tier2_docs,
    _check_missing_unit_tests,
    _check_mypy_disabled,
    _check_oversized_frontend,
    _check_oversized_python,
    _check_parallel_tests,
    _check_pr_template,
    _check_pydantic_v1,
    _check_pytest_timeouts,
    _check_relative_imports,
    _check_ruff_sprawl,
    _check_security_workflow,
    _check_service_boundaries,
    _check_skill_prompts_complete,
    _check_stale_runbooks,
    _check_test_skips,
    _check_todo_backlog,
    _check_tool_schema_completeness,
    _check_unvalidated_env,
    _check_workflow_secrets,
)
from .catalog_definitions import SEED_FINDINGS
from .catalog_helpers import (
    _EXCLUDED_DIRS,
    _find_pyprojects,
    _is_excluded,
    _line_count,
    _load_yaml,
    _match_count,
    _py_files,
    _pyproject_sections,
    _read_lines,
    _source_files,
    _walk_files,
)


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


__all__ = [
    "FindingCatalog",
    "SEED_FINDINGS",
    "AuditArea",
    "Confidence",
    "Finding",
    "Severity",
    "_BARE_EXCEPT_RE",
    "_CROSS_LAYER_RE",
    "_ENV_ACCESS_RE",
    "_EXCLUDED_DIRS",
    "_GUARDRAIL_RE",
    "_HTTP_CALL_RE",
    "_IDEMPOTENCY_RE",
    "_PYDANTIC_V1_RE",
    "_RELATIVE_IMPORT_RE",
    "_SECRET_RE",
    "_SKIP_WITHOUT_REASON_RE",
    "_TIER1_DOCS",
    "_TIER2_DOCS",
    "_TODO_FIXME_RE",
    "_check_adr_gaps",
    "_check_agents_md_audit_rules",
    "_check_bare_excepts",
    "_check_ci_timeouts",
    "_check_conflicting_claims",
    "_check_contract_drift",
    "_check_coverage_config",
    "_check_deep_nesting",
    "_check_dependabot",
    "_check_dependency_pinning",
    "_check_duplicate_files",
    "_check_fast_unit_marker",
    "_check_graceful_shutdown",
    "_check_hardcoded_secrets",
    "_check_health_endpoints",
    "_check_http_timeouts",
    "_check_idempotency_gaps",
    "_check_infisical_barrier",
    "_check_llm_guardrails",
    "_check_migration_downgrades",
    "_check_missing_debug_config",
    "_check_missing_repo_audit_skill",
    "_check_missing_tier1_docs",
    "_check_missing_tier2_docs",
    "_check_missing_unit_tests",
    "_check_mypy_disabled",
    "_check_oversized_frontend",
    "_check_oversized_python",
    "_check_parallel_tests",
    "_check_pr_template",
    "_check_pydantic_v1",
    "_check_pytest_timeouts",
    "_check_relative_imports",
    "_check_ruff_sprawl",
    "_check_security_workflow",
    "_check_service_boundaries",
    "_check_skill_prompts_complete",
    "_check_stale_runbooks",
    "_check_test_skips",
    "_check_todo_backlog",
    "_check_tool_schema_completeness",
    "_check_unvalidated_env",
    "_check_workflow_secrets",
    "_find_pyprojects",
    "_is_excluded",
    "_line_count",
    "_load_yaml",
    "_match_count",
    "_py_files",
    "_pyproject_sections",
    "_read_lines",
    "_source_files",
    "_walk_files",
]


class _FindingCatalogModule(types.ModuleType):
    """Module wrapper ensuring backward-compatible attribute mutation (e.g., monkeypatching)."""

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if hasattr(catalog_checks, name):
            setattr(catalog_checks, name, value)
        if hasattr(catalog_helpers, name):
            setattr(catalog_helpers, name, value)
        if hasattr(catalog_definitions, name):
            setattr(catalog_definitions, name, value)


sys.modules[__name__].__class__ = _FindingCatalogModule
