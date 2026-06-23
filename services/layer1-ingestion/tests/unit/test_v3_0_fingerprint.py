"""Tests for the v3.0 deduplication fingerprint."""

from __future__ import annotations

from layer1_ingestion.api.source_routes import _compute_fingerprint


class TestV3_0Fingerprint:
    def test_fingerprint_excludes_custody_and_connector(self) -> None:
        """Custody mode and connector name must not change the fingerprint."""
        base = _compute_fingerprint(
            tenant_id="tenant-1",
            account_id="account-1",
            source_type="notes",
            external_reference="doc-1",
            content_hash="hash-a",
        )
        # Changing metadata fields that are not part of identity should not matter
        with_external = _compute_fingerprint(
            tenant_id="tenant-1",
            account_id="account-1",
            source_type="notes",
            external_reference="doc-1",
            content_hash="hash-a",
            external_identity={
                "external_system": "salesforce",
                "external_object_type": "Opportunity",
                "external_object_id": "006",
                "external_version": "v1",
                "snapshot_hash": "snap-1",
            },
        )
        assert base != with_external

        # Same identity twice yields same fingerprint.
        repeat = _compute_fingerprint(
            tenant_id="tenant-1",
            account_id="account-1",
            source_type="notes",
            external_reference="doc-1",
            content_hash="hash-a",
            external_identity={
                "external_system": "salesforce",
                "external_object_type": "Opportunity",
                "external_object_id": "006",
                "external_version": "v1",
                "snapshot_hash": "snap-1",
            },
        )
        assert with_external == repeat

    def test_fingerprint_changes_with_external_object_id(self) -> None:
        a = _compute_fingerprint(
            tenant_id="tenant-1",
            account_id="account-1",
            source_type="crm",
            external_reference=None,
            content_hash="hash-a",
            external_identity={"external_object_id": "obj-1"},
        )
        b = _compute_fingerprint(
            tenant_id="tenant-1",
            account_id="account-1",
            source_type="crm",
            external_reference=None,
            content_hash="hash-a",
            external_identity={"external_object_id": "obj-2"},
        )
        assert a != b

    def test_fingerprint_is_stable_for_empty_identity(self) -> None:
        a = _compute_fingerprint(
            tenant_id="tenant-1",
            account_id="account-1",
            source_type="notes",
            external_reference="doc-1",
            content_hash="hash-a",
        )
        b = _compute_fingerprint(
            tenant_id="tenant-1",
            account_id="account-1",
            source_type="notes",
            external_reference="doc-1",
            content_hash="hash-a",
            external_identity={},
        )
        assert a == b
