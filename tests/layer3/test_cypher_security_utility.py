"""Unit tests for utils.cypher_security (GOV-L3-006).

Verifies 100% coverage of the consolidated Cypher safety utility:
- validate_cypher_identifier: allowlist enforcement for dynamic identifiers
- validate_tenant_scoped_cypher: static query template validator
- TENANT_OWNED_LABELS: canonical label registry completeness
- ALLOWED_REL_TYPES / ALLOWED_TARGET_LABELS: dynamic identifier allowlists
- Backward-compat shim: cypher_scope_guard re-exports the same symbols
"""

from __future__ import annotations

import pytest

from layer3_knowledge.utils.cypher_security import (
    ALLOWED_REL_TYPES,
    ALLOWED_TARGET_LABELS,
    TENANT_OWNED_LABELS,
    validate_cypher_identifier,
    validate_tenant_scoped_cypher,
)


# ---------------------------------------------------------------------------
# validate_cypher_identifier
# ---------------------------------------------------------------------------

class TestValidateCypherIdentifier:
    """validate_cypher_identifier must accept allowlisted values and reject others."""

    def test_accepts_allowed_rel_type(self):
        for rel in ALLOWED_REL_TYPES:
            validate_cypher_identifier(rel, ALLOWED_REL_TYPES, kind="rel_type")

    def test_accepts_allowed_target_label(self):
        for label in ALLOWED_TARGET_LABELS:
            validate_cypher_identifier(label, ALLOWED_TARGET_LABELS, kind="target_label")

    def test_rejects_unknown_rel_type(self):
        with pytest.raises(ValueError, match="rel_type"):
            validate_cypher_identifier("UNKNOWN_REL", ALLOWED_REL_TYPES, kind="rel_type")

    def test_rejects_unknown_target_label(self):
        with pytest.raises(ValueError, match="target_label"):
            validate_cypher_identifier("MaliciousLabel", ALLOWED_TARGET_LABELS, kind="target_label")

    def test_error_message_includes_value(self):
        with pytest.raises(ValueError, match="injected_label"):
            validate_cypher_identifier("injected_label", ALLOWED_TARGET_LABELS, kind="target_label")

    def test_error_message_includes_allowlist(self):
        with pytest.raises(ValueError, match="Allowed:"):
            validate_cypher_identifier("bad", ALLOWED_REL_TYPES, kind="rel_type")

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError):
            validate_cypher_identifier("", ALLOWED_REL_TYPES, kind="rel_type")

    def test_case_sensitive(self):
        """Allowlist check is case-sensitive — 'hasdriver' != 'hasDriver'."""
        with pytest.raises(ValueError):
            validate_cypher_identifier("hasdriver", ALLOWED_REL_TYPES, kind="rel_type")

    def test_custom_allowlist(self):
        custom = frozenset({"LabelA", "LabelB"})
        validate_cypher_identifier("LabelA", custom, kind="label")
        with pytest.raises(ValueError):
            validate_cypher_identifier("LabelC", custom, kind="label")


# ---------------------------------------------------------------------------
# validate_tenant_scoped_cypher
# ---------------------------------------------------------------------------

class TestValidateTenantScopedCypher:
    """validate_tenant_scoped_cypher must reject unscoped tenant-owned label reads."""

    _OWNED = {"Product", "Feature", "PainSignal"}

    def test_accepts_inline_tenant_filter(self):
        validate_tenant_scoped_cypher(
            "MATCH (p:Product {tenant_id: $tenant_id}) RETURN p",
            tenant_owned_labels=self._OWNED,
        )

    def test_accepts_where_predicate(self):
        validate_tenant_scoped_cypher(
            "MATCH (p:Product) WHERE p.tenant_id = $tenant_id RETURN p",
            tenant_owned_labels=self._OWNED,
        )

    def test_accepts_unowned_label_without_filter(self):
        """Labels not in tenant_owned_labels do not require a tenant filter."""
        validate_tenant_scoped_cypher(
            "MATCH (n:Industry) RETURN n",
            tenant_owned_labels=self._OWNED,
        )

    def test_rejects_unscoped_match(self):
        with pytest.raises(ValueError, match="missing tenant_id filter"):
            validate_tenant_scoped_cypher(
                "MATCH (p:Product) RETURN p",
                tenant_owned_labels=self._OWNED,
            )

    def test_rejects_unscoped_optional_match(self):
        with pytest.raises(ValueError, match="missing tenant_id filter"):
            validate_tenant_scoped_cypher(
                "MATCH (p:Product {tenant_id: $tenant_id}) "
                "OPTIONAL MATCH (f:Feature) RETURN f",
                tenant_owned_labels=self._OWNED,
            )

    def test_error_includes_label_name(self):
        with pytest.raises(ValueError, match="Product"):
            validate_tenant_scoped_cypher(
                "MATCH (p:Product) RETURN p",
                tenant_owned_labels=self._OWNED,
            )

    def test_uses_canonical_labels_by_default(self):
        """When tenant_owned_labels is omitted, TENANT_OWNED_LABELS is used."""
        with pytest.raises(ValueError, match="missing tenant_id filter"):
            validate_tenant_scoped_cypher("MATCH (a:Account) RETURN a")

    def test_query_name_appears_in_error(self):
        with pytest.raises(ValueError, match="my_query"):
            validate_tenant_scoped_cypher(
                "MATCH (p:Product) RETURN p",
                tenant_owned_labels=self._OWNED,
                query_name="my_query",
            )


# ---------------------------------------------------------------------------
# TENANT_OWNED_LABELS completeness
# ---------------------------------------------------------------------------

class TestTenantOwnedLabels:
    """TENANT_OWNED_LABELS must contain the expected core labels."""

    _REQUIRED = {
        "Account", "ValuePack", "Formula", "ValueDriver",
        "BenchmarkDataset", "Evidence", "PainSignal", "Workflow",
    }

    def test_contains_required_labels(self):
        missing = self._REQUIRED - TENANT_OWNED_LABELS
        assert not missing, f"TENANT_OWNED_LABELS is missing required labels: {missing}"

    def test_is_frozenset(self):
        assert isinstance(TENANT_OWNED_LABELS, frozenset)

    def test_allowed_target_labels_subset_of_tenant_owned(self):
        """Every dynamic target label must also be a tenant-owned label."""
        not_owned = ALLOWED_TARGET_LABELS - TENANT_OWNED_LABELS
        assert not not_owned, (
            f"ALLOWED_TARGET_LABELS contains labels not in TENANT_OWNED_LABELS: {not_owned}"
        )


# ---------------------------------------------------------------------------
# Allowlist registry completeness
# ---------------------------------------------------------------------------

class TestAllowlists:
    """ALLOWED_REL_TYPES and ALLOWED_TARGET_LABELS must be frozensets."""

    def test_rel_types_is_frozenset(self):
        assert isinstance(ALLOWED_REL_TYPES, frozenset)

    def test_target_labels_is_frozenset(self):
        assert isinstance(ALLOWED_TARGET_LABELS, frozenset)

    def test_rel_types_non_empty(self):
        assert len(ALLOWED_REL_TYPES) > 0

    def test_target_labels_non_empty(self):
        assert len(ALLOWED_TARGET_LABELS) > 0

    def test_rel_types_and_target_labels_are_paired(self):
        """Each rel_type should have a corresponding target_label and vice versa."""
        # hasDriver → ValueDriver, hasFormula → Formula, etc.
        expected_pairs = {
            "hasDriver": "ValueDriver",
            "hasFormula": "Formula",
            "hasBenchmark": "BenchmarkDataset",
            "hasWorkflow": "Workflow",
        }
        for rel, label in expected_pairs.items():
            assert rel in ALLOWED_REL_TYPES, f"Missing rel_type: {rel}"
            assert label in ALLOWED_TARGET_LABELS, f"Missing target_label: {label}"


# ---------------------------------------------------------------------------
# Backward-compatibility shim
# ---------------------------------------------------------------------------

class TestCypherScopeGuardShim:
    """cypher_scope_guard must re-export the same symbols from the new utility."""

    def test_shim_exports_validate_tenant_scoped_cypher(self):
        from layer3_knowledge.services.cypher_scope_guard import (
            validate_tenant_scoped_cypher as shim_fn,
        )
        assert shim_fn is validate_tenant_scoped_cypher

    def test_shim_exports_tenant_owned_labels(self):
        from layer3_knowledge.services.cypher_scope_guard import (
            TENANT_OWNED_LABELS as shim_labels,
        )
        assert shim_labels is TENANT_OWNED_LABELS

    def test_shim_validate_works_end_to_end(self):
        """Shim callers get the same behaviour as direct utility callers."""
        from layer3_knowledge.services.cypher_scope_guard import (
            validate_tenant_scoped_cypher as shim_fn,
        )
        # Should pass
        shim_fn(
            "MATCH (p:Product {tenant_id: $tenant_id}) RETURN p",
            tenant_owned_labels={"Product"},
        )
        # Should raise
        with pytest.raises(ValueError, match="missing tenant_id filter"):
            shim_fn(
                "MATCH (p:Product) RETURN p",
                tenant_owned_labels={"Product"},
            )
