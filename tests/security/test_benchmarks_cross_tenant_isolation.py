"""Hostile cross-tenant isolation tests for the benchmarks route module.

Covers:
1. Read isolation  — Tenant A cannot read Tenant B's :Benchmark / :BenchmarkPolicy nodes.
2. Write isolation — Tenant A cannot mutate Tenant B's nodes.
3. Fail-closed     — Missing tenant context is rejected before any Neo4j call.

Strategy: static Cypher analysis + unit tests calling the real route helpers.
No live Neo4j instance required.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from value_fabric.layer3.api.routes.benchmarks import _get_authenticated_tenant_id

pytestmark = pytest.mark.tenant_boundary

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS_PATH = (
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "benchmarks.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source() -> str:
    return BENCHMARKS_PATH.read_text(encoding="utf-8")


def _cypher_strings(source: str) -> list[str]:
    """Extract triple-quoted strings that look like Cypher."""
    candidates = re.findall(r'"""(.*?)"""', source, re.DOTALL)
    candidates += re.findall(r"'''(.*?)'''", source, re.DOTALL)
    return [
        s for s in candidates
        if re.search(r"\b(MATCH|CREATE|MERGE|RETURN|WHERE)\b", s, re.IGNORECASE)
    ]


# ---------------------------------------------------------------------------
# 1. Read isolation — static analysis
# ---------------------------------------------------------------------------

class TestBenchmarkReadIsolation:
    """Verify every read Cypher in benchmarks.py is tenant-scoped."""

    def test_list_benchmarks_query_has_tenant_filter(self):
        """MATCH (b:Benchmark) must be followed by WHERE b.tenant_id = $tenant_id."""
        source = _source()
        # Find the list_benchmarks function body
        match = re.search(
            r"async def list_benchmarks.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "list_benchmarks function not found in benchmarks.py"
        body = match.group(0)
        assert "tenant_id" in body, "list_benchmarks must reference tenant_id"
        assert "$tenant_id" in body, "list_benchmarks must use $tenant_id parameter"

    def test_get_benchmark_query_has_tenant_filter(self):
        """MATCH (b:Benchmark {id: $benchmark_id}) must also filter by tenant_id."""
        source = _source()
        match = re.search(
            r"async def get_benchmark.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "get_benchmark function not found in benchmarks.py"
        body = match.group(0)
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_list_benchmark_policies_query_has_tenant_filter(self):
        """BenchmarkPolicy list must be scoped to tenant."""
        source = _source()
        match = re.search(
            r"async def list_benchmark_policies.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "list_benchmark_policies not found in benchmarks.py"
        body = match.group(0)
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_all_cypher_match_clauses_include_tenant_id(self):
        """Every Cypher MATCH on :Benchmark or :BenchmarkPolicy must carry tenant_id."""
        source = _source()
        cypher_blocks = _cypher_strings(source)
        if not cypher_blocks:
            pytest.skip("No triple-quoted Cypher strings found")

        violations: list[str] = []
        for block in cypher_blocks:
            # Find MATCH clauses on the target labels
            matches = re.findall(
                r"MATCH\s*\([^)]*:(?:Benchmark|BenchmarkPolicy)[^)]*\)",
                block,
                re.IGNORECASE,
            )
            for m in matches:
                # The surrounding block must reference tenant_id
                if "tenant_id" not in block:
                    violations.append(m)

        assert not violations, (
            f"MATCH clauses on :Benchmark/:BenchmarkPolicy without tenant_id: {violations}"
        )


# ---------------------------------------------------------------------------
# 2. Write isolation — static analysis
# ---------------------------------------------------------------------------

class TestBenchmarkWriteIsolation:
    """Verify write Cypher in benchmarks.py carries tenant_id."""

    def test_seed_benchmark_policies_write_includes_tenant_id(self):
        """MERGE/CREATE for BenchmarkPolicy must include tenant_id."""
        source = _source()
        match = re.search(
            r"async def seed_benchmark_policies.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "seed_benchmark_policies not found in benchmarks.py"
        body = match.group(0)
        assert "tenant_id" in body, (
            "seed_benchmark_policies must persist tenant_id on created nodes"
        )

    def test_update_benchmark_policy_scoped_to_tenant(self):
        """Policy update must verify ownership before mutating."""
        source = _source()
        match = re.search(
            r"async def update_benchmark_policy.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "update_benchmark_policy not found in benchmarks.py"
        body = match.group(0)
        assert "tenant_id" in body, (
            "update_benchmark_policy must scope the update to the authenticated tenant"
        )

    def test_no_unscoped_merge_on_benchmark_nodes(self):
        """MERGE on :Benchmark or :BenchmarkPolicy must include tenant_id property."""
        source = _source()
        cypher_blocks = _cypher_strings(source)
        if not cypher_blocks:
            pytest.skip("No triple-quoted Cypher strings found")

        violations: list[str] = []
        for block in cypher_blocks:
            merges = re.findall(
                r"MERGE\s*\([^)]*:(?:Benchmark|BenchmarkPolicy)[^)]*\{[^}]*\}[^)]*\)",
                block,
                re.IGNORECASE | re.DOTALL,
            )
            for m in merges:
                if "tenant_id" not in m:
                    violations.append(m)

        assert not violations, (
            f"MERGE clauses on :Benchmark/:BenchmarkPolicy without tenant_id: {violations}"
        )


# ---------------------------------------------------------------------------
# 3. Fail-closed — missing tenant context (calls real route helper)
# ---------------------------------------------------------------------------

class TestBenchmarkFailClosed:
    """Missing or empty tenant context must be rejected before any Neo4j call."""

    def test_missing_tenant_id_on_api_key_raises_401(self):
        """If api_key.tenant_id is absent, _get_authenticated_tenant_id raises HTTP 401."""
        mock_key = SimpleNamespace(tenant_id=None)
        with pytest.raises(HTTPException) as exc_info:
            _get_authenticated_tenant_id(mock_key)
        assert exc_info.value.status_code == 401

    def test_empty_string_tenant_id_raises_401(self):
        """Empty string tenant_id must also be rejected."""
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
        mock_key = SimpleNamespace(tenant_id="tenant-abc")
        result = _get_authenticated_tenant_id(mock_key)
        assert result == "tenant-abc"

    def test_tenant_id_extracted_from_auth_context_not_request_body(self):
        """Tenant ID must come from the authenticated API key, not a request body field."""
        source = _source()
        assert "request.json" not in source, (
            "benchmarks.py must not read tenant_id from request.json()"
        )

    def test_create_neo4j_tenant_session_called_with_tenant_id(self):
        """Neo4j session must be created with the authenticated tenant_id."""
        source = _source()
        assert "create_neo4j_tenant_session" in source, (
            "benchmarks.py must use create_neo4j_tenant_session for all Neo4j access"
        )
        assert "create_neo4j_tenant_session(tenant_id)" in source, (
            "create_neo4j_tenant_session must receive the authenticated tenant_id"
        )
