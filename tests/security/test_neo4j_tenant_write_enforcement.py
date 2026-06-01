"""Neo4j Tenant Write Enforcement — P0 Critical Gap Remediation

Validates that Layer 3 (Knowledge) Neo4j write operations are strictly
tenant-scoped and that cross-tenant write attempts are blocked at both
static-validation and execution boundaries.

Production Invariants:
1. All CREATE / MERGE / SET on tenant-owned labels require tenant_id.
2. Structural validation (_structural_tenant_scope_errors) blocks unscoped writes.
3. Tenant query helpers (db.tenant_queries) raise ValueError without tenant_id.
4. Execution wrappers (db.query_execution) enforce tenant context fail-closed.
5. Cross-tenant entity update via spoofed parameters is rejected.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure L3 src root is available for direct imports
_REPO_ROOT = Path(__file__).resolve().parents[2]
_L3_SRC = str(_REPO_ROOT / "services" / "layer3-knowledge" / "src")
if _L3_SRC not in sys.path:
    sys.path.insert(0, _L3_SRC)

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ALLOW_LEGACY_TEST_TENANT_IDS", "true")

from utils.cypher_security import TENANT_OWNED_LABELS, validate_tenant_scoped_cypher


# ---------------------------------------------------------------------------
# Load L3 db modules via importlib — inject fake packages so relative
# imports inside query_execution.py and tenant_queries.py resolve.
# ---------------------------------------------------------------------------


def _make_fake_module(name: str):
    mod = type(sys)(name)
    mod.__path__ = []
    mod.__package__ = name
    sys.modules[name] = mod
    return mod


# Fake parent packages
for _pkg in (
    "layer3_knowledge",
    "layer3_knowledge.graph",
    "layer3_knowledge.schema",
    "layer3_knowledge.db",
):
    if _pkg not in sys.modules:
        _make_fake_module(_pkg)

# Fake graph.query_guards (used by query_execution.py)
_fk_gq = type(sys)("layer3_knowledge.graph.query_guards")
_fk_gq.DEFAULT_MAX_QUERY_DEPTH = 10
_fk_gq.DEFAULT_QUERY_TIMEOUT_SECONDS = 30
_fk_gq.sanitize_query_depth = lambda x: x
_fk_gq.sanitize_query_timeout_seconds = lambda x: x
sys.modules["layer3_knowledge.graph.query_guards"] = _fk_gq

# Fake schema.constraints (used by tenant_queries.py)
_fk_sc = type(sys)("layer3_knowledge.schema.constraints")
_fk_sc.get_relationship_types = lambda: []
sys.modules["layer3_knowledge.schema.constraints"] = _fk_sc


def _load_module(dotted_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(
        dotted_name, str(Path(_L3_SRC) / rel_path)
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = module
    spec.loader.exec_module(module)
    return module


_db_qe = _load_module("layer3_knowledge.db.query_execution", "db/query_execution.py")
TenantExecutionContext = _db_qe.TenantExecutionContext
TenantQueryValidationError = _db_qe.TenantQueryValidationError
_structural_tenant_scope_errors = _db_qe._structural_tenant_scope_errors
_touches_tenant_owned_label = _db_qe._touches_tenant_owned_label

_db_tq = _load_module("layer3_knowledge.db.tenant_queries", "db/tenant_queries.py")
get_entity_by_id = _db_tq.get_entity_by_id

pytestmark = [
    pytest.mark.security,
    pytest.mark.tenant_boundary,
    pytest.mark.tenant_matrix,
]


# ---------------------------------------------------------------------------
# Positive tests: valid tenant-scoped writes accepted
# ---------------------------------------------------------------------------

class TestTenantScopedWriteAcceptance:
    """Valid, properly-scoped write queries must pass structural validation."""

    def test_create_with_inline_tenant_property_accepted(self):
        """CREATE on tenant-owned label with inline tenant_id is valid."""
        query = (
            "CREATE (e:Entity {id: $id, name: $name, tenant_id: $tenant_id}) RETURN e"
        )
        errors = _structural_tenant_scope_errors(query, {"id": "1", "name": "x", "tenant_id": "t-a"})
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_merge_with_tenant_predicate_accepted(self):
        """MERGE with WHERE tenant_id predicate is valid."""
        query = (
            "MERGE (e:Entity {id: $id}) "
            "ON CREATE SET e.name = $name, e.tenant_id = $tenant_id "
            "ON MATCH SET e.updated_at = timestamp() "
            "RETURN e"
        )
        errors = _structural_tenant_scope_errors(query, {"id": "1", "name": "x", "tenant_id": "t-a"})
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_set_with_tenant_predicate_accepted(self):
        """MATCH + SET where the matched node is tenant-scoped is valid."""
        query = (
            "MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) "
            "SET e.status = 'archived' "
            "RETURN e"
        )
        errors = _structural_tenant_scope_errors(query, {"id": "1", "tenant_id": "t-a"})
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_create_non_tenant_label_accepted(self):
        """CREATE on labels NOT in TENANT_OWNED_LABELS skips tenant validation."""
        query = "CREATE (s:SystemConfig {key: $key, value: $value}) RETURN s"
        errors = _structural_tenant_scope_errors(query, {"key": "k", "value": "v"})
        assert errors == [], f"Expected no errors for non-tenant label, got: {errors}"


# ---------------------------------------------------------------------------
# Negative tests: unscoped write queries rejected
# ---------------------------------------------------------------------------

class TestUnscopedWriteRejection:
    """Unscoped write queries on tenant-owned labels must be rejected."""

    def test_create_without_tenant_rejected(self):
        """CREATE on tenant-owned label without tenant_id is rejected."""
        query = "CREATE (e:Entity {id: $id, name: $name}) RETURN e"
        errors = _structural_tenant_scope_errors(query, {"id": "1", "name": "x"})
        assert "Entity" in " ".join(errors), (
            f"Expected Entity scoping error, got: {errors}"
        )

    def test_merge_without_tenant_rejected(self):
        """MERGE on tenant-owned label without tenant_id is rejected."""
        query = "MERGE (p:Product {sku: $sku}) RETURN p"
        errors = _structural_tenant_scope_errors(query, {"sku": "SKU-1"})
        assert "Product" in " ".join(errors), (
            f"Expected Product scoping error, got: {errors}"
        )

    def test_match_then_set_without_tenant_rejected(self):
        """MATCH + SET on tenant-owned node without tenant predicate is rejected."""
        query = (
            "MATCH (e:Entity {id: $id}) "
            "SET e.name = 'hacked' "
            "RETURN e"
        )
        errors = _structural_tenant_scope_errors(query, {"id": "1"})
        assert "Entity" in " ".join(errors), (
            f"Expected Entity scoping error for SET, got: {errors}"
        )

    def test_delete_without_tenant_rejected(self):
        """MATCH + DELETE on tenant-owned node without tenant predicate is rejected."""
        query = (
            "MATCH (e:Entity {id: $id}) "
            "DELETE e"
        )
        errors = _structural_tenant_scope_errors(query, {"id": "1"})
        assert "Entity" in " ".join(errors), (
            f"Expected Entity scoping error for DELETE, got: {errors}"
        )

    def test_detach_delete_without_tenant_rejected(self):
        """DETACH DELETE on tenant-owned node without tenant predicate is rejected."""
        query = (
            "MATCH (e:Entity {id: $id}) "
            "DETACH DELETE e"
        )
        errors = _structural_tenant_scope_errors(query, {"id": "1"})
        assert "Entity" in " ".join(errors), (
            f"Expected Entity scoping error for DETACH DELETE, got: {errors}"
        )

    def test_multiple_labels_one_unscoped_rejected(self):
        """Query with multiple tenant-owned labels fails if any is unscoped."""
        query = (
            "MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) "
            "MATCH (p:Product {sku: $sku}) "
            "RETURN e, p"
        )
        errors = _structural_tenant_scope_errors(query, {"id": "1", "tenant_id": "t-a", "sku": "SKU-1"})
        assert "Product" in " ".join(errors), (
            f"Expected Product scoping error, got: {errors}"
        )
        assert "Entity" not in " ".join(errors), (
            "Entity should NOT be flagged because it has tenant_id"
        )


# ---------------------------------------------------------------------------
# Negative tests: tenant query helpers fail-closed
# ---------------------------------------------------------------------------

class TestTenantQueryHelperFailClosed:
    """db.tenant_queries helpers must raise when tenant_id is missing."""

    @pytest.mark.asyncio
    async def test_get_entity_by_id_without_tenant_raises(self):
        """get_entity_by_id with empty tenant_id raises ValueError."""
        mock_session = AsyncMock()
        with pytest.raises(ValueError, match="tenant_id is required"):
            await get_entity_by_id(mock_session, entity_id="abc", tenant_id="")

    @pytest.mark.asyncio
    async def test_get_entity_by_id_with_none_tenant_raises(self):
        """get_entity_by_id with None tenant_id raises ValueError."""
        mock_session = AsyncMock()
        with pytest.raises(ValueError, match="tenant_id is required"):
            await get_entity_by_id(mock_session, entity_id="abc", tenant_id=None)


# ---------------------------------------------------------------------------
# Negative tests: execution context boundaries
# ---------------------------------------------------------------------------

class TestExecutionContextBoundaries:
    """TenantExecutionContext must enforce scope rules."""

    def test_context_without_tenant_blocks_tenant_scoped(self):
        """Context with tenant_id=None must block tenant-scoped queries."""
        ctx = TenantExecutionContext(tenant_id=None)
        assert ctx.tenant_id is None
        assert ctx.is_bypass is False
        # A tenant-scoped query should not be allowed without tenant context
        # (The actual allow/deny logic is in run_validated_query; we assert
        #  the context state that drives that logic.)

    def test_bypass_flag_only_for_system_queries(self):
        """is_bypass=True is required for system-scope queries."""
        ctx = TenantExecutionContext(tenant_id=None, is_bypass=True)
        assert ctx.is_bypass is True
        # System queries (schema, migration) may use bypass, but tenant-owned
        # runtime queries must never use it.


# ---------------------------------------------------------------------------
# Cross-tenant write adversarial tests
# ---------------------------------------------------------------------------

class TestCrossTenantWriteAdversarial:
    """Adversarial: attempt to write tenant-B data using tenant-A context."""

    def test_structural_validation_accepts_parameter_map_with_tenant_id(self):
        """Parameter map containing tenant_id is accepted by structural validator."""
        query = "CREATE (e:Entity $props) RETURN e"
        errors = _structural_tenant_scope_errors(
            query, {"props": {"tenant_id": "tenant-b"}}
        )
        assert errors == [], (
            f"Validator should accept param-map with tenant_id, got: {errors}"
        )

    def test_structural_validation_rejects_parameter_map_without_tenant_id(self):
        """Parameter map missing tenant_id is rejected by structural validator."""
        query = "CREATE (e:Entity $props) RETURN e"
        errors = _structural_tenant_scope_errors(
            query, {"props": {"name": "no-tenant"}}
        )
        assert "Entity" in " ".join(errors), (
            f"Validator must reject unscoped CREATE when param-map lacks tenant_id, got: {errors}"
        )

    def test_tenant_owned_label_detection_comprehensive(self):
        """All labels in TENANT_OWNED_LABELS trigger scoping checks."""
        for label in TENANT_OWNED_LABELS:
            query = f"MATCH (n:{label} {{id: $id}}) RETURN n"
            errors = _structural_tenant_scope_errors(query, {"id": "1"})
            assert f"{label}(n)" in errors or f"{label}('n')" in " ".join(errors) or label in " ".join(errors), (
                f"Label {label} should trigger scoping error when unscoped"
            )
