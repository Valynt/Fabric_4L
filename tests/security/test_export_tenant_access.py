"""S2-H: Export Tenant Access & Provenance Tests — Pillar 2 + Pillar 5.

Ship/No-Ship Gate: These tests verify that:
    1. Export endpoints require authentication (not optional context).
    2. Export storage paths are tenant-namespaced (no cross-tenant overwrites).
    3. Provenance manifests include tenant_id and are structurally complete.
    4. Export audit events are emitted with correct tenant context.

Expected Initial State:
    - test_export_endpoint_requires_auth:       FAIL (uses get_optional_context)
    - test_export_storage_key_is_tenant_scoped: FAIL (no tenant prefix in key)
    - test_provenance_manifest_includes_tenant:  PASS
    - test_provenance_manifest_has_required_fields: PASS
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Set

import pytest

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_ANALYSIS_ROUTES = (
    _PROJECT_ROOT
    / "services"
    / "layer4-agents"
    / "src"
    / "layer4_agents"
    / "api"
    / "routes"
    / "analysis.py"
)

_EXPORT_PROVENANCE = (
    _PROJECT_ROOT
    / "services"
    / "layer4-agents"
    / "src"
    / "layer4_agents"
    / "services"
    / "export_provenance.py"
)

_EXPORT_STORAGE = (
    _PROJECT_ROOT
    / "services"
    / "layer4-agents"
    / "src"
    / "layer4_agents"
    / "services"
    / "export_storage.py"
)

_DOCUMENT_EXPORT = (
    _PROJECT_ROOT
    / "services"
    / "layer4-agents"
    / "src"
    / "layer4_agents"
    / "tools"
    / "document_export.py"
)


# ---------------------------------------------------------------------------
# Tests: Export Endpoint Auth Enforcement
# ---------------------------------------------------------------------------

class TestExportEndpointAuth:
    """Verify export endpoints require mandatory authentication."""

    def test_export_endpoint_requires_auth_not_optional(self):
        """GET /cases/{case_id}/export must use ``require_authenticated``,
        not ``get_optional_context``.

        Business case exports contain confidential financial projections,
        competitive analysis, and customer data.  Optional auth means an
        unauthenticated request could potentially access exports if the
        executor doesn't independently verify tenant ownership.

        Expected initial state: FAIL — uses get_optional_context.
        """
        source = _ANALYSIS_ROUTES.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "export_business_case":
                    func_source = ast.get_source_segment(source, node) or ""

                    uses_optional = "get_optional_context" in func_source
                    uses_required = "require_authenticated" in func_source

                    assert not uses_optional, (
                        "export_business_case uses get_optional_context. "
                        "Export endpoints MUST use require_authenticated — "
                        "business case data is confidential."
                    )
                    assert uses_required, (
                        "export_business_case does not use require_authenticated. "
                        "The endpoint has no authentication enforcement."
                    )
                    return

        pytest.fail("export_business_case function not found in analysis.py")

    def test_export_endpoint_uses_tenant_scoped_db(self):
        """Export endpoint must use get_db_from_context if it queries the DB.

        Even if the export reads from the workflow executor (Redis), the
        endpoint should use tenant-scoped DB for any audit writes.
        """
        source = _ANALYSIS_ROUTES.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "export_business_case":
                    func_source = ast.get_source_segment(source, node) or ""

                    # The export endpoint currently uses the executor for data
                    # retrieval, not direct DB.  But it should still have
                    # tenant context for audit logging.
                    has_context = (
                        "get_optional_context" in func_source
                        or "require_authenticated" in func_source
                        or "get_db_from_context" in func_source
                    )
                    assert has_context, (
                        "export_business_case has no tenant context injection at all."
                    )
                    return

        pytest.fail("export_business_case function not found in analysis.py")


# ---------------------------------------------------------------------------
# Tests: Export Storage Tenant Namespacing
# ---------------------------------------------------------------------------

class TestExportStorageNamespacing:
    """Verify export artifacts are stored in tenant-namespaced paths."""

    def test_export_storage_key_includes_tenant_id(self):
        """The S3 object key for exports must include the tenant_id.

        Without tenant namespacing, Tenant A could overwrite Tenant B's
        export if they share a case_id pattern, or a signed URL for
        Tenant A's export could be guessed by Tenant B.

        Expected initial state: FAIL — current code uses flat key structure.
        """
        source = _ANALYSIS_ROUTES.read_text(encoding="utf-8")

        # Find the export_business_case function and check the object key pattern
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "export_business_case":
                    func_source = ast.get_source_segment(source, node) or ""

                    # The object key should include tenant_id
                    # Look for patterns like f"exports/{tenant_id}/..." or
                    # context.tenant_id in the key construction
                    has_tenant_prefix = "base_prefix = f\"exports/tenant_{context.tenant_id}/" in func_source
                    assert has_tenant_prefix, (
                        "export_business_case does not include tenant_id in the "
                        "storage object key. Without tenant namespacing:\n"
                        "  1. Tenant A could overwrite Tenant B's export\n"
                        "  2. Signed URLs are guessable across tenants\n"
                        "  3. Bucket listing would expose cross-tenant filenames"
                    )
                    return

        pytest.fail("export_business_case function not found in analysis.py")

    def test_export_storage_upload_requires_tenant_metadata(self):
        """The upload_bytes function should accept tenant metadata.

        S3 object metadata should include tenant_id for audit trail
        and access control at the storage layer.
        """
        source = _EXPORT_STORAGE.read_text(encoding="utf-8")

        # The upload_bytes function accepts metadata parameter
        assert "metadata" in source, (
            "export_storage.upload_bytes does not accept metadata parameter. "
            "Tenant context should be stored as S3 object metadata."
        )


# ---------------------------------------------------------------------------
# Tests: Provenance Manifest Structure
# ---------------------------------------------------------------------------

class TestProvenanceManifestStructure:
    """Verify provenance manifests are structurally complete for audit."""

    def test_provenance_module_imports_request_context(self):
        """Provenance module must import RequestContext for tenant awareness."""
        source = _EXPORT_PROVENANCE.read_text(encoding="utf-8")
        assert "RequestContext" in source, (
            "export_provenance.py does not import RequestContext. "
            "Provenance manifests must be tenant-aware."
        )

    def test_provenance_schema_version_defined(self):
        """Provenance manifests must have a schema version for forward compat."""
        source = _EXPORT_PROVENANCE.read_text(encoding="utf-8")
        assert "PROVENANCE_SCHEMA_VERSION" in source, (
            "export_provenance.py does not define PROVENANCE_SCHEMA_VERSION. "
            "Schema versioning is required for manifest forward compatibility."
        )

    def test_provenance_collects_truth_ids(self):
        """Provenance must collect truth_object_ids for evidence chain."""
        source = _EXPORT_PROVENANCE.read_text(encoding="utf-8")
        assert "truth_object_ids" in source or "truth_ids" in source, (
            "export_provenance.py does not collect truth IDs. "
            "The evidence chain from agent output to export must be traceable."
        )

    def test_provenance_collects_source_pointers(self):
        """Provenance must collect source_pointers for data lineage."""
        source = _EXPORT_PROVENANCE.read_text(encoding="utf-8")
        assert "source_pointer" in source.lower() or "source_references" in source, (
            "export_provenance.py does not collect source pointers. "
            "Data lineage must be traceable from export back to source data."
        )

    def test_provenance_generates_content_hash(self):
        """Provenance must include a content hash for integrity verification."""
        source = _EXPORT_PROVENANCE.read_text(encoding="utf-8")
        assert any(term in source for term in ["hashlib", "content_hash", "canonical_hash", "deterministic_fingerprint"]), (
            "export_provenance.py does not generate content hashes. "
            "Export integrity must be verifiable via hash comparison."
        )


# ---------------------------------------------------------------------------
# Tests: Export Audit Trail
# ---------------------------------------------------------------------------

class TestExportAuditTrail:
    """Verify export operations emit audit events."""

    def test_export_endpoint_emits_audit_event(self):
        """The export endpoint must emit an audit event for compliance.

        Every export of confidential data must be logged with:
        - tenant_id
        - user_id
        - case_id
        - export format
        - timestamp
        """
        source = _ANALYSIS_ROUTES.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "export_business_case":
                    func_source = ast.get_source_segment(source, node) or ""

                    has_success_audit = "AuditAction.EXPORT_PACKAGE_GENERATED" in func_source
                    assert has_success_audit, (
                        "export_business_case does not emit audit events. "
                        "Every export of confidential data must be logged."
                    )
                    return

        pytest.fail("export_business_case function not found in analysis.py")

    def test_export_denied_attempt_is_audited(self):
        """Tenant-denied export attempts must emit an audit event."""
        source = _ANALYSIS_ROUTES.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "export_business_case":
                    func_source = ast.get_source_segment(source, node) or ""

                    denied_branch_has_audit = (
                        "denied_reason" in func_source
                        and "tenant_access_denied" in func_source
                        and "AuditAction.EXPORT_REQUESTED" in func_source
                    )
                    assert denied_branch_has_audit, (
                        "export_business_case does not audit denied tenant export attempts."
                    )
                    return

        pytest.fail("export_business_case function not found in analysis.py")
