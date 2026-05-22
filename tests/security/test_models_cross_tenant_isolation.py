"""Hostile cross-tenant isolation tests for the models_router route module.

Covers:
1. Read isolation  — Tenant A cannot read Tenant B's :ValueModel nodes.
2. Write isolation — Tenant A cannot create or delete Tenant B's nodes.
3. Fail-closed     — Missing tenant context is rejected before any Neo4j call.

Strategy: static Cypher analysis + unit tests calling the real auth helper.
No live Neo4j instance required.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from value_fabric.layer3.api.auth_context import TenantBearerContext, extract_tenant_from_bearer
from starlette.requests import Request as StarletteRequest

pytestmark = pytest.mark.tenant_boundary

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_ROUTER_PATH = (
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "models_router.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source() -> str:
    return MODELS_ROUTER_PATH.read_text(encoding="utf-8")


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

class TestModelReadIsolation:
    """Every read Cypher in models_router.py must be tenant-scoped."""

    def test_list_models_has_tenant_filter(self):
        """Model list must filter by tenant_id."""
        source = _source()
        match = re.search(
            r"async def list_models.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "list_models not found in models_router.py"
        body = match.group(0)
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_get_model_detail_has_tenant_filter(self):
        """Model detail lookup must scope to tenant."""
        source = _source()
        match = re.search(
            r"async def get_model_detail.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "get_model_detail not found in models_router.py"
        body = match.group(0)
        assert "tenant_id" in body
        assert "$tenant_id" in body

    def test_get_folder_counts_has_tenant_filter(self):
        """Folder count aggregation must be scoped to tenant."""
        source = _source()
        match = re.search(
            r"async def get_folder_counts.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "get_folder_counts not found in models_router.py"
        body = match.group(0)
        assert "tenant_id" in body

    def test_all_cypher_match_on_valuemodel_nodes_include_tenant_id(self):
        """Every MATCH on :ValueModel must carry tenant_id."""
        source = _source()
        cypher_blocks = _cypher_strings(source)
        if not cypher_blocks:
            pytest.skip("No triple-quoted Cypher strings found")

        violations: list[str] = []
        for block in cypher_blocks:
            matches = re.findall(
                r"MATCH\s*\([^)]*:(?:ValueModel|Model)[^)]*\)",
                block,
                re.IGNORECASE,
            )
            for m in matches:
                if "tenant_id" not in block:
                    violations.append(m)

        assert not violations, (
            f"MATCH clauses on :ValueModel without tenant_id: {violations}"
        )


# ---------------------------------------------------------------------------
# 2. Write isolation — static analysis
# ---------------------------------------------------------------------------

class TestModelWriteIsolation:
    """Write Cypher in models_router.py must carry tenant_id."""

    def test_create_model_persists_tenant_id(self):
        """CREATE/MERGE for :ValueModel must include tenant_id."""
        source = _source()
        match = re.search(
            r"async def create_model.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "create_model not found in models_router.py"
        body = match.group(0)
        assert "tenant_id" in body, (
            "create_model must persist tenant_id on the created node"
        )

    def test_delete_model_scoped_to_tenant(self):
        """Model deletion must verify ownership before deleting."""
        source = _source()
        match = re.search(
            r"async def delete_model.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "delete_model not found in models_router.py"
        body = match.group(0)
        assert "tenant_id" in body, (
            "delete_model must scope the DELETE to the authenticated tenant"
        )

    def test_no_unscoped_delete_on_model_nodes(self):
        """DELETE on :ValueModel must be preceded by a tenant-scoped MATCH."""
        source = _source()
        cypher_blocks = _cypher_strings(source)
        if not cypher_blocks:
            pytest.skip("No triple-quoted Cypher strings found")

        # Any block containing DETACH DELETE or DELETE must also contain tenant_id
        violations: list[str] = []
        for block in cypher_blocks:
            if re.search(r"\b(DETACH\s+)?DELETE\b", block, re.IGNORECASE):
                if "tenant_id" not in block:
                    violations.append(block[:120])

        assert not violations, (
            f"DELETE Cypher blocks without tenant_id scoping: {violations}"
        )


# ---------------------------------------------------------------------------
# 3. Fail-closed — missing tenant context (calls real auth helper)
# ---------------------------------------------------------------------------

def _make_request(auth_header: str = "", tenant_header: str = "") -> StarletteRequest:
    """Build a minimal Starlette Request with the given headers."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"authorization", auth_header.encode()),
            (b"x-tenant-id", tenant_header.encode()),
        ],
    }
    return StarletteRequest(scope)


def _bearer(payload: dict) -> str:
    import base64, json
    def enc(d): return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"Bearer {enc({'alg':'none'})}.{enc(payload)}.sig"


class TestModelFailClosed:
    """Missing or empty tenant context must be rejected before any Neo4j call."""

    def test_missing_auth_header_raises_401(self):
        """No Authorization header must raise HTTP 401."""
        req = _make_request(auth_header="")
        with pytest.raises(HTTPException) as exc_info:
            extract_tenant_from_bearer(req)
        assert exc_info.value.status_code == 401

    def test_missing_tenant_id_claim_raises_401(self):
        """JWT with no tenant_id claim must raise HTTP 401."""
        req = _make_request(auth_header=_bearer({"sub": "user-1"}))
        with pytest.raises(HTTPException) as exc_info:
            extract_tenant_from_bearer(req)
        assert exc_info.value.status_code == 401

    def test_conflicting_tenant_header_raises_403(self):
        """X-Tenant-ID that differs from JWT claim must raise HTTP 403."""
        req = _make_request(
            auth_header=_bearer({"tenant_id": "tenant-a"}),
            tenant_header="tenant-b",
        )
        with pytest.raises(HTTPException) as exc_info:
            extract_tenant_from_bearer(req)
        assert exc_info.value.status_code == 403

    def test_valid_bearer_returns_tenant_bearer_context(self):
        """Valid JWT returns a TenantBearerContext with correct fields."""
        req = _make_request(
            auth_header=_bearer({"tenant_id": "tenant-a", "sub": "user-1"}),
            tenant_header="tenant-a",
        )
        ctx = extract_tenant_from_bearer(req)
        assert isinstance(ctx, TenantBearerContext)
        assert ctx.tenant_id == "tenant-a"
        assert ctx.user_id == "user-1"

    def test_tenant_id_from_ctx_not_request_body(self):
        """models_router.py must extract tenant_id from the request context."""
        source = _source()
        assert "ctx.tenant_id" in source, (
            "models_router.py must extract tenant_id from the request context (ctx.tenant_id)"
        )
        assert "request.json" not in source, (
            "models_router.py must not read tenant_id from request.json()"
        )

    def test_execute_query_used_for_all_db_access(self):
        """All Neo4j access must go through the tenant session's execute_query."""
        source = _source()
        assert "execute_query" in source, (
            "models_router.py must use execute_query on the tenant-scoped Neo4j session"
        )
