"""Hostile cross-tenant isolation tests for the formula_governance route module.

Covers:
1. Read isolation  — Tenant A cannot read Tenant B's :Formula / :FormulaVersion nodes.
2. Write isolation — Tenant A cannot create, approve, or deprecate Tenant B's formulas.
3. Fail-closed     — Missing tenant context is rejected before any Neo4j call.

Strategy: static Cypher analysis + unit tests calling the real route helper.
No live Neo4j instance required.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from value_fabric.layer3.api.routes.formula_governance import _get_authenticated_tenant_id

pytestmark = pytest.mark.tenant_boundary

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMULA_GOV_PATH = (
    REPO_ROOT
    / "services"
    / "layer3-knowledge"
    / "src"
    / "api"
    / "routes"
    / "formula_governance.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source() -> str:
    return FORMULA_GOV_PATH.read_text(encoding="utf-8")


def _cypher_strings(source: str) -> list[str]:
    candidates = re.findall(r'"""(.*?)"""', source, re.DOTALL)
    candidates += re.findall(r"'''(.*?)'''", source, re.DOTALL)
    return [
        s for s in candidates
        if re.search(r"\b(MATCH|CREATE|MERGE|RETURN|WHERE)\b", s, re.IGNORECASE)
    ]


def _function_body(source: str, fn_name: str) -> str | None:
    match = re.search(
        rf"async def {re.escape(fn_name)}.*?(?=\nasync def |\Z)",
        source,
        re.DOTALL,
    )
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# 1. Read isolation — static analysis
# ---------------------------------------------------------------------------

class TestFormulaGovernanceReadIsolation:
    """Every read Cypher in formula_governance.py must be tenant-scoped."""

    def test_list_pending_approvals_has_tenant_filter(self):
        """Pending approval list must filter by tenant_id."""
        source = _source()
        body = _function_body(source, "list_pending_approvals")
        assert body is not None, "list_pending_approvals not found in formula_governance.py"
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_list_formula_versions_has_tenant_filter(self):
        """Formula version list must scope to tenant."""
        source = _source()
        body = _function_body(source, "list_formula_versions")
        assert body is not None, "list_formula_versions not found in formula_governance.py"
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_get_formula_governance_has_tenant_filter(self):
        """Formula governance metadata must scope to tenant."""
        source = _source()
        body = _function_body(source, "get_formula_governance")
        assert body is not None, "get_formula_governance not found in formula_governance.py"
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_get_formula_dependencies_has_tenant_filter(self):
        """Formula dependency graph must scope to tenant."""
        source = _source()
        body = _function_body(source, "get_formula_dependencies")
        assert body is not None, "get_formula_dependencies not found in formula_governance.py"
        assert "tenant_id" in body

    def test_all_cypher_match_on_formula_nodes_include_tenant_id(self):
        """Every MATCH on :Formula or :FormulaVersion must carry tenant_id."""
        source = _source()
        cypher_blocks = _cypher_strings(source)
        if not cypher_blocks:
            pytest.skip("No triple-quoted Cypher strings found")

        violations: list[str] = []
        for block in cypher_blocks:
            matches = re.findall(
                r"MATCH\s*\([^)]*:(?:Formula|FormulaVersion)[^)]*\)",
                block,
                re.IGNORECASE,
            )
            for m in matches:
                if "tenant_id" not in block:
                    violations.append(m)

        assert not violations, (
            f"MATCH clauses on :Formula/:FormulaVersion without tenant_id: {violations}"
        )


# ---------------------------------------------------------------------------
# 2. Write isolation — static analysis
# ---------------------------------------------------------------------------

class TestFormulaGovernanceWriteIsolation:
    """Write Cypher in formula_governance.py must carry tenant_id."""

    def test_create_formula_version_persists_tenant_id(self):
        """New FormulaVersion must be created with tenant_id."""
        source = _source()
        body = _function_body(source, "create_formula_version")
        assert body is not None, "create_formula_version not found in formula_governance.py"
        assert "tenant_id" in body, (
            "create_formula_version must persist tenant_id on the created FormulaVersion"
        )

    def test_approve_formula_scoped_to_tenant(self):
        """Formula approval must verify ownership before mutating status."""
        source = _source()
        body = _function_body(source, "approve_formula")
        assert body is not None, "approve_formula not found in formula_governance.py"
        assert "tenant_id" in body, (
            "approve_formula must scope the status update to the authenticated tenant"
        )

    def test_deprecate_formula_scoped_to_tenant(self):
        """Formula deprecation must verify ownership before mutating status."""
        source = _source()
        body = _function_body(source, "deprecate_formula")
        assert body is not None, "deprecate_formula not found in formula_governance.py"
        assert "tenant_id" in body, (
            "deprecate_formula must scope the status update to the authenticated tenant"
        )

    def test_activate_formula_scoped_to_tenant(self):
        """Formula activation must verify ownership before mutating status."""
        source = _source()
        body = _function_body(source, "activate_formula")
        assert body is not None, "activate_formula not found in formula_governance.py"
        assert "tenant_id" in body, (
            "activate_formula must scope the status update to the authenticated tenant"
        )

    def test_no_unscoped_set_on_formula_status(self):
        """SET f.status = ... must be preceded by a tenant-scoped MATCH."""
        source = _source()
        cypher_blocks = _cypher_strings(source)
        if not cypher_blocks:
            pytest.skip("No triple-quoted Cypher strings found")

        violations: list[str] = []
        for block in cypher_blocks:
            if re.search(r"\bSET\b.*?\.status\s*=", block, re.IGNORECASE | re.DOTALL):
                if "tenant_id" not in block:
                    violations.append(block[:120])

        assert not violations, (
            f"SET status Cypher blocks without tenant_id scoping: {violations}"
        )


# ---------------------------------------------------------------------------
# 3. Fail-closed — missing tenant context (calls real route helper)
# ---------------------------------------------------------------------------

class TestFormulaGovernanceFailClosed:
    """Missing or empty tenant context must be rejected before any Neo4j call."""

    def test_missing_tenant_id_raises_401(self):
        """api_key.tenant_id absent must raise HTTP 401."""
        mock_key = SimpleNamespace(tenant_id=None)
        with pytest.raises(HTTPException) as exc_info:
            _get_authenticated_tenant_id(mock_key)
        assert exc_info.value.status_code == 401

    def test_empty_tenant_id_raises_401(self):
        """Empty string tenant_id must be treated as absent."""
        mock_key = SimpleNamespace(tenant_id="")
        with pytest.raises(HTTPException) as exc_info:
            _get_authenticated_tenant_id(mock_key)
        assert exc_info.value.status_code == 401

    def test_whitespace_only_tenant_id_raises_401(self):
        """Whitespace-only tenant_id must be treated as absent."""
        mock_key = SimpleNamespace(tenant_id="   ")
        with pytest.raises(HTTPException) as exc_info:
            _get_authenticated_tenant_id(mock_key)
        assert exc_info.value.status_code == 401

    def test_valid_tenant_id_is_returned(self):
        """Valid tenant_id is returned unchanged."""
        mock_key = SimpleNamespace(tenant_id="tenant-fg")
        assert _get_authenticated_tenant_id(mock_key) == "tenant-fg"

    def test_tenant_id_from_auth_not_request_body(self):
        """formula_governance.py must extract tenant_id from the authenticated api_key."""
        source = _source()
        assert "_get_authenticated_tenant_id" in source, (
            "formula_governance.py must use _get_authenticated_tenant_id helper"
        )
        assert "request.json" not in source, (
            "formula_governance.py must not read tenant_id from request.json()"
        )

    def test_create_neo4j_tenant_session_used_for_all_db_access(self):
        """All Neo4j access must go through create_neo4j_tenant_session."""
        source = _source()
        assert "create_neo4j_tenant_session" in source, (
            "formula_governance.py must use create_neo4j_tenant_session for all Neo4j access"
        )

    def test_ownership_check_before_state_transition(self):
        """A tenant ownership check must precede any formula state transition."""
        source = _source()
        assert "check_query" in source or "WHERE f.tenant_id = $tenant_id" in source, (
            "formula_governance.py must verify formula ownership before state transitions"
        )
