"""Hostile cross-tenant isolation tests for the variables route module.

Covers:
1. Read isolation  — Tenant A cannot read Tenant B's :Variable / :SourceBinding nodes.
2. Write isolation — Tenant A cannot create or mutate Tenant B's nodes.
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

from value_fabric.layer3.api.routes.variables import _get_authenticated_tenant_id

pytestmark = pytest.mark.tenant_boundary

REPO_ROOT = Path(__file__).resolve().parents[2]
VARIABLES_PATH = (
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "variables.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source() -> str:
    return VARIABLES_PATH.read_text(encoding="utf-8")


def _cypher_strings(source: str) -> list[str]:
    candidates = re.findall(r'"""(.*?)"""', source, re.DOTALL)
    candidates += re.findall(r"'''(.*?)'''", source, re.DOTALL)
    return [
        s for s in candidates
        if re.search(r"\b(MATCH|CREATE|MERGE|RETURN|WHERE)\b", s, re.IGNORECASE)
    ]


# ---------------------------------------------------------------------------
# 1. Read isolation — static analysis
# ---------------------------------------------------------------------------

class TestVariableReadIsolation:
    """Every read Cypher in variables.py must be tenant-scoped."""

    def test_search_variables_has_tenant_filter(self):
        """Variable search must filter by tenant_id."""
        source = _source()
        match = re.search(
            r"async def search_variables.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "search_variables not found in variables.py"
        body = match.group(0)
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_get_variable_has_tenant_filter(self):
        """Variable detail lookup must scope to tenant."""
        source = _source()
        match = re.search(
            r"async def get_variable.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "get_variable not found in variables.py"
        body = match.group(0)
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_list_source_bindings_has_tenant_filter(self):
        """SourceBinding list must be scoped to tenant."""
        source = _source()
        match = re.search(
            r"async def list_source_bindings.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "list_source_bindings not found in variables.py"
        body = match.group(0)
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_get_variable_stats_has_tenant_filter(self):
        """Variable stats must be scoped to tenant."""
        source = _source()
        match = re.search(
            r"async def get_variable_stats.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "get_variable_stats not found in variables.py"
        body = match.group(0)
        assert "tenant_id" in body

    def test_all_cypher_match_on_variable_nodes_include_tenant_id(self):
        """Every MATCH on :Variable or :SourceBinding must carry tenant_id."""
        source = _source()
        cypher_blocks = _cypher_strings(source)
        if not cypher_blocks:
            pytest.skip("No triple-quoted Cypher strings found")

        violations: list[str] = []
        for block in cypher_blocks:
            matches = re.findall(
                r"MATCH\s*\([^)]*:(?:Variable|SourceBinding)[^)]*\)",
                block,
                re.IGNORECASE,
            )
            for m in matches:
                if "tenant_id" not in block:
                    violations.append(m)

        assert not violations, (
            f"MATCH clauses on :Variable/:SourceBinding without tenant_id: {violations}"
        )


# ---------------------------------------------------------------------------
# 2. Write isolation — static analysis
# ---------------------------------------------------------------------------

class TestVariableWriteIsolation:
    """Write Cypher in variables.py must carry tenant_id."""

    def test_create_variable_persists_tenant_id(self):
        """CREATE/MERGE for :Variable must include tenant_id."""
        source = _source()
        match = re.search(
            r"async def create_variable.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "create_variable not found in variables.py"
        body = match.group(0)
        assert "tenant_id" in body, (
            "create_variable must persist tenant_id on the created node"
        )

    def test_update_variable_scoped_to_tenant(self):
        """Variable update must verify ownership before mutating."""
        source = _source()
        match = re.search(
            r"async def update_variable.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "update_variable not found in variables.py"
        body = match.group(0)
        assert "tenant_id" in body, (
            "update_variable must scope the update to the authenticated tenant"
        )

    def test_no_unscoped_create_on_variable_nodes(self):
        """CREATE on :Variable must include tenant_id in the property map."""
        source = _source()
        cypher_blocks = _cypher_strings(source)
        if not cypher_blocks:
            pytest.skip("No triple-quoted Cypher strings found")

        violations: list[str] = []
        for block in cypher_blocks:
            creates = re.findall(
                r"CREATE\s*\([^)]*:Variable[^)]*\{[^}]+\}[^)]*\)",
                block,
                re.IGNORECASE | re.DOTALL,
            )
            for c in creates:
                if "tenant_id" not in c:
                    violations.append(c)

        assert not violations, (
            f"CREATE clauses on :Variable without tenant_id: {violations}"
        )


# ---------------------------------------------------------------------------
# 3. Fail-closed — missing tenant context (calls real route helper)
# ---------------------------------------------------------------------------

class TestVariableFailClosed:
    """Missing or empty tenant context must be rejected before any Neo4j call."""

    def test_missing_tenant_id_raises_401(self):
        """_get_authenticated_tenant_id raises HTTP 401 when tenant_id is absent."""
        mock_key = SimpleNamespace(tenant_id=None)
        with pytest.raises(HTTPException) as exc_info:
            _get_authenticated_tenant_id(mock_key)
        assert exc_info.value.status_code == 401

    def test_whitespace_only_tenant_id_raises_401(self):
        """Whitespace-only tenant_id must be treated as absent."""
        mock_key = SimpleNamespace(tenant_id="   ")
        with pytest.raises(HTTPException) as exc_info:
            _get_authenticated_tenant_id(mock_key)
        assert exc_info.value.status_code == 401

    def test_empty_string_tenant_id_raises_401(self):
        """Empty string tenant_id must be rejected."""
        mock_key = SimpleNamespace(tenant_id="")
        with pytest.raises(HTTPException) as exc_info:
            _get_authenticated_tenant_id(mock_key)
        assert exc_info.value.status_code == 401

    def test_valid_tenant_id_is_returned(self):
        """Valid tenant_id is returned unchanged."""
        mock_key = SimpleNamespace(tenant_id="tenant-xyz")
        assert _get_authenticated_tenant_id(mock_key) == "tenant-xyz"

    def test_tenant_id_from_auth_not_request_body(self):
        """variables.py must extract tenant_id from the authenticated api_key."""
        source = _source()
        assert "_get_authenticated_tenant_id" in source, (
            "variables.py must use _get_authenticated_tenant_id helper"
        )
        assert "request.json" not in source, (
            "variables.py must not read tenant_id from request.json()"
        )

    def test_create_neo4j_tenant_session_used_for_all_db_access(self):
        """All Neo4j access must go through create_neo4j_tenant_session."""
        source = _source()
        assert "create_neo4j_tenant_session" in source, (
            "variables.py must use create_neo4j_tenant_session for all Neo4j access"
        )
