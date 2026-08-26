"""Neo4j write isolation tests — P0 gap remediation.

Validates that Cypher write operations (CREATE, MERGE, SET, DELETE) in
Layer 3 include tenant_id scoping so Tenant A cannot write to or corrupt
Tenant B's graph data.

Production Invariant: Every write Cypher must bind tenant_id from the
authenticated request context, not from the request body.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_layer3_source() -> str:
    """Return concatenated source of all Layer 3 Python files."""
    roots = [
        Path("value_fabric/layer3"),
        Path("services/layer3-knowledge/src"),
    ]
    parts: list[str] = []
    for root in roots:
        if root.exists():
            for path in root.rglob("*.py"):
                if "__pycache__" not in path.parts:
                    parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Static analysis: write Cypher patterns must carry tenant_id
# ---------------------------------------------------------------------------


class TestNeo4jWriteStaticAnalysis:
    """Verify write Cypher patterns in source carry tenant_id constraints."""

    def test_create_patterns_include_tenant_id(self):
        """Every Cypher CREATE clause that sets entity properties must include tenant_id.

        Scoped to triple-quoted Cypher strings to avoid false positives from
        Python docstrings, log messages, and non-Cypher code.
        """
        source = _collect_layer3_source()
        if not source:
            pytest.skip("Layer 3 source not available")

        # Extract only triple-quoted strings that look like Cypher
        # (contain MATCH, CREATE, MERGE, or RETURN keywords)
        cypher_strings = re.findall(r'"""(.*?)"""', source, re.DOTALL)
        cypher_strings += re.findall(r"'''(.*?)'''", source, re.DOTALL)
        cypher_strings = [
            s
            for s in cypher_strings
            if re.search(r"\b(MATCH|CREATE|MERGE|RETURN|WHERE)\b", s, re.IGNORECASE)
        ]

        if not cypher_strings:
            pytest.skip(
                "No Cypher triple-quoted strings found — source may use a different pattern"
            )

        # Within those Cypher strings, find CREATE (...{...}) blocks
        create_blocks = []
        for cypher in cypher_strings:
            blocks = re.findall(
                r"CREATE\s*\([^)]*\{[^}]+\}[^)]*\)",
                cypher,
                re.DOTALL | re.IGNORECASE,
            )
            create_blocks.extend(blocks)

        if not create_blocks:
            pytest.skip("No CREATE property blocks found in Cypher strings")

        # Known legitimate exceptions:
        # - PROVActivity nodes are W3C PROV audit records (infrastructure metadata,
        #   not tenant-scoped data). They intentionally omit tenant_id.
        _exempt_labels = {"PROVActivity", "PROVEntity", "PROVAgent"}

        def _is_exempt(block: str) -> bool:
            return any(label in block for label in _exempt_labels)

        missing = [
            b for b in create_blocks if "tenant_id" not in b and not _is_exempt(b)
        ]
        assert not missing, (
            f"Found {len(missing)} CREATE block(s) in Cypher strings missing tenant_id:\n"
            + "\n".join(missing[:3])
        )

    def test_merge_patterns_include_tenant_id(self):
        """MERGE clauses that create nodes must include tenant_id in the match key."""
        source = _collect_layer3_source()
        if not source:
            pytest.skip("Layer 3 source not available")

        merge_blocks = re.findall(
            r"MERGE\s*\([^)]*\{[^}]+\}[^)]*\)",
            source,
            re.DOTALL | re.IGNORECASE,
        )
        if not merge_blocks:
            pytest.skip("No MERGE property blocks found")

        missing = [b for b in merge_blocks if "tenant_id" not in b]
        assert not missing, (
            f"Found {len(missing)} MERGE block(s) missing tenant_id:\n"
            + "\n".join(missing[:3])
        )

    def test_set_clauses_do_not_overwrite_tenant_id_with_null(self):
        """SET clauses must not set tenant_id to NULL or empty string."""
        source = _collect_layer3_source()
        if not source:
            pytest.skip("Layer 3 source not available")

        # Patterns like: SET n.tenant_id = null  or  SET n.tenant_id = ''
        dangerous = re.findall(
            r"SET\s+\w+\.tenant_id\s*=\s*(null|''|\"\")",
            source,
            re.IGNORECASE,
        )
        assert not dangerous, f"Found SET clauses that clear tenant_id: {dangerous}"

    def test_delete_clauses_include_tenant_id_filter(self):
        """Cypher DELETE operations must be in queries that filter on tenant_id.

        Scoped to triple-quoted strings that contain Cypher keywords to avoid
        false positives from Python docstrings describing delete operations.
        """
        source = _collect_layer3_source()
        if not source:
            pytest.skip("Layer 3 source not available")

        # Extract triple-quoted strings that look like Cypher
        cypher_strings = re.findall(r'"""(.*?)"""', source, re.DOTALL)
        cypher_strings += re.findall(r"'''(.*?)'''", source, re.DOTALL)

        # Keep only strings that contain Cypher structural keywords
        # (MATCH + DELETE together is the canonical Cypher delete pattern)
        delete_queries = [
            s
            for s in cypher_strings
            if re.search(r"\bMATCH\b", s, re.IGNORECASE)
            and re.search(r"\b(?:DETACH\s+)?DELETE\b", s, re.IGNORECASE)
        ]

        if not delete_queries:
            pytest.skip("No Cypher MATCH+DELETE queries found")

        missing = [q for q in delete_queries if "tenant_id" not in q]
        assert not missing, (
            f"Found {len(missing)} Cypher DELETE query/queries missing tenant_id filter:\n"
            + "\n".join(q[:300] for q in missing[:3])
        )

    def test_write_queries_use_parameterised_tenant_id(self):
        """Cypher write queries must use $tenant_id parameter, not string interpolation.

        Checks triple-quoted Cypher strings for f-string injection of tenant_id
        directly into the query body. Log messages and error strings are excluded.
        """
        source = _collect_layer3_source()
        if not source:
            pytest.skip("Layer 3 source not available")

        # Extract triple-quoted strings that look like Cypher write operations
        cypher_strings = re.findall(r'"""(.*?)"""', source, re.DOTALL)
        cypher_strings += re.findall(r"'''(.*?)'''", source, re.DOTALL)
        write_cypher = [
            s
            for s in cypher_strings
            if re.search(r"\b(CREATE|MERGE|SET|DELETE)\b", s, re.IGNORECASE)
            and re.search(r"\b(MATCH|WHERE)\b", s, re.IGNORECASE)
        ]

        # Within those Cypher strings, look for tenant_id values that are
        # interpolated directly (not via $tenant_id parameter).
        # Legitimate patterns excluded:
        #   - tenant_id: $tenant_id          — correct parameterisation
        #   - tenant_id: entity.tenant_id    — bulk ingestion property read
        #   - tenant_id: rel.tenant_id       — relationship property read
        #   - n.tenant_id / node.tenant_id   — property accessor in WHERE clause
        _safe_suffixes = (
            "$tenant_id",  # parameterised
            "entity.tenant_id",  # bulk ingestion object property
            "rel.tenant_id",  # relationship object property
        )

        injections = []
        for cypher in write_cypher:
            matches = re.findall(
                r"tenant_id\s*:\s*([^\s,}\n]+)",
                cypher,
                re.IGNORECASE,
            )
            bad = [
                m
                for m in matches
                if not any(m.strip().startswith(safe) for safe in _safe_suffixes)
                and not m.strip().startswith("$")
                and not re.match(
                    r"^\w+\.tenant_id$", m.strip()
                )  # any obj.tenant_id read
            ]
            injections.extend(bad)

        assert not injections, (
            f"Found {len(injections)} potential tenant_id injection(s) in Cypher "
            f"write queries — use $tenant_id parameter instead:\n"
            + "\n".join(injections[:5])
        )


# ---------------------------------------------------------------------------
# Mock-based: write endpoints enforce tenant context from JWT, not body
# ---------------------------------------------------------------------------


class TestNeo4jWriteTenantEnforcement:
    """Verify write operations bind tenant_id from authenticated context."""

    @pytest.mark.asyncio
    async def test_entity_create_uses_jwt_tenant_not_body(self):
        """P0: Entity creation must use JWT tenant_id, not a body-supplied value."""
        try:
            from src.api.main import (
                NEO4J_TENANT_AVAILABLE,
                create_entity,
            )
        except ImportError:
            pytest.skip("Layer 3 not available")

        if not NEO4J_TENANT_AVAILABLE:
            pytest.skip("Neo4j tenant support not available")

        jwt_tenant = str(uuid.uuid4())
        body_tenant = str(uuid.uuid4())  # attacker-supplied, different from JWT

        mock_context = MagicMock()
        mock_context.tenant_id = jwt_tenant

        mock_request = MagicMock()
        mock_request.state.governance_context = mock_context

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = {"entity_id": "new-entity-1"}
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        # Build a minimal entity payload that includes a body-level tenant_id
        try:
            from src.api.main import EntityCreateRequest

            payload = EntityCreateRequest(
                entity_type="Company",
                properties={"name": "Acme", "tenant_id": body_tenant},
            )
        except (ImportError, TypeError):
            pytest.skip("EntityCreateRequest not available or incompatible")

        try:
            await create_entity(
                entity=payload,
                neo4j_driver=mock_driver,
                request=mock_request,
            )
        except Exception:
            pass  # 422/404 acceptable — we only care about what was written

        # The Cypher write must have used jwt_tenant, not body_tenant
        for call in mock_session.run.call_args_list:
            args = call[0]
            kwargs = call[1] if len(call) > 1 else {}
            params = kwargs if kwargs else (args[1] if len(args) > 1 else {})
            if isinstance(params, dict) and "tenant_id" in params:
                assert params["tenant_id"] == jwt_tenant, (
                    f"Write used body tenant_id '{params['tenant_id']}' "
                    f"instead of JWT tenant_id '{jwt_tenant}'. "
                    "P0: Cross-tenant write via body injection."
                )

    @pytest.mark.asyncio
    async def test_entity_update_scoped_to_jwt_tenant(self):
        """P0: Entity update must only affect nodes owned by the JWT tenant."""
        try:
            from src.api.main import (
                NEO4J_TENANT_AVAILABLE,
                update_entity,
            )
        except ImportError:
            pytest.skip("Layer 3 not available")

        if not NEO4J_TENANT_AVAILABLE:
            pytest.skip("Neo4j tenant support not available")

        jwt_tenant = str(uuid.uuid4())
        entity_id = "entity-owned-by-tenant-b"

        mock_context = MagicMock()
        mock_context.tenant_id = jwt_tenant

        mock_request = MagicMock()
        mock_request.state.governance_context = mock_context

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None  # Not found — correct for cross-tenant
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        try:
            await update_entity(
                entity_id=entity_id,
                properties={"name": "Hijacked"},
                neo4j_driver=mock_driver,
                request=mock_request,
            )
        except Exception:
            pass

        # Every Cypher call must include tenant_id scoping
        for call in mock_session.run.call_args_list:
            args = call[0]
            query = args[0] if args else ""
            assert "tenant_id" in query, (
                f"Update query missing tenant_id filter: {query!r}. "
                "P0: Tenant A can update Tenant B nodes."
            )

    @pytest.mark.asyncio
    async def test_entity_delete_scoped_to_jwt_tenant(self):
        """P0: Entity deletion must only affect nodes owned by the JWT tenant."""
        try:
            from src.api.main import (
                NEO4J_TENANT_AVAILABLE,
                delete_entity,
            )
        except ImportError:
            pytest.skip("Layer 3 not available")

        if not NEO4J_TENANT_AVAILABLE:
            pytest.skip("Neo4j tenant support not available")

        jwt_tenant = str(uuid.uuid4())
        entity_id = "entity-owned-by-tenant-b"

        mock_context = MagicMock()
        mock_context.tenant_id = jwt_tenant

        mock_request = MagicMock()
        mock_request.state.governance_context = mock_context

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        try:
            await delete_entity(
                entity_id=entity_id,
                neo4j_driver=mock_driver,
                request=mock_request,
            )
        except Exception:
            pass

        for call in mock_session.run.call_args_list:
            args = call[0]
            query = args[0] if args else ""
            if re.search(r"\bDELETE\b", query, re.IGNORECASE):
                assert "tenant_id" in query, (
                    f"DELETE query missing tenant_id filter: {query!r}. "
                    "P0: Tenant A can delete Tenant B nodes."
                )

    @pytest.mark.asyncio
    async def test_batch_write_all_operations_scoped_to_jwt_tenant(self):
        """P0: Batch write operations must all use JWT tenant_id."""
        try:
            from src.api.main import (
                NEO4J_TENANT_AVAILABLE,
                BatchEntityOperation,
                BatchEntityRequest,
                batch_entity_operations,
            )
        except ImportError:
            pytest.skip("Layer 3 not available")

        if not NEO4J_TENANT_AVAILABLE:
            pytest.skip("Neo4j tenant support not available")

        jwt_tenant = str(uuid.uuid4())

        mock_context = MagicMock()
        mock_context.tenant_id = jwt_tenant

        mock_request = MagicMock()
        mock_request.state.governance_context = mock_context

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = {"entity_id": "e1"}
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        try:
            batch_request = BatchEntityRequest(
                operations=[
                    BatchEntityOperation(
                        operation="create",
                        properties={"name": "New Node"},
                    ),
                    BatchEntityOperation(
                        operation="update",
                        entity_id="existing-node",
                        properties={"name": "Updated"},
                    ),
                ],
                atomic=False,
            )
            await batch_entity_operations(
                request=batch_request,
                neo4j_driver=mock_driver,
                fastapi_request=mock_request,
            )
        except Exception:
            pass

        write_calls = [
            call
            for call in mock_session.run.call_args_list
            if re.search(
                r"\b(CREATE|MERGE|SET|DELETE)\b",
                call[0][0] if call[0] else "",
                re.IGNORECASE,
            )
        ]
        for call in write_calls:
            args = call[0]
            kwargs = call[1] if len(call) > 1 else {}
            query = args[0] if args else ""
            params = kwargs if kwargs else (args[1] if len(args) > 1 else {})
            assert "tenant_id" in query or (
                isinstance(params, dict) and params.get("tenant_id") == jwt_tenant
            ), (
                f"Batch write missing tenant_id scope. Query: {query!r}, Params: {params}"
            )
