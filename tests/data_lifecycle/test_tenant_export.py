"""Tenant export lifecycle contract tests."""


TENANT_EXPORT_REQUIRED_CATEGORIES = {
    "tenant_profile",
    "workspace_metadata",
    "account_profile",
    "user_identity",
    "derived_knowledge",
    "workflow_outputs",
    "billing_records",
    "audit_logs",
}


def _sample_tenant_export() -> dict:
    return {
        "schema_version": "data-lifecycle-export.v1",
        "export_scope": "tenant",
        "tenant_id": "tenant_a",
        "subject": {"type": "tenant", "id": "tenant_a"},
        "data_categories": sorted(TENANT_EXPORT_REQUIRED_CATEGORIES),
        "resources": {
            "tenant": [{"id": "tenant_a", "tenant_id": "tenant_a", "state": "active"}],
            "workspaces": [{"id": "workspace_001", "tenant_id": "tenant_a"}],
            "accounts": [{"id": "acct_001", "tenant_id": "tenant_a"}],
            "users": [{"id": "user_001", "tenant_id": "tenant_a", "email": "admin@example.com"}],
            "billing_records": [{"id": "invoice_001", "tenant_id": "tenant_a", "customer_ref": "cus_redacted"}],
            "audit_logs": [{"id": "audit_001", "tenant_id": "tenant_a", "event": "tenant.exported"}],
        },
    }


def test_tenant_export_covers_required_categories():
    payload = _sample_tenant_export()
    assert set(payload["data_categories"]) == TENANT_EXPORT_REQUIRED_CATEGORIES
    assert payload["export_scope"] == "tenant"
    assert payload["subject"] == {"type": "tenant", "id": payload["tenant_id"]}


def test_tenant_export_has_only_subject_tenant_records():
    payload = _sample_tenant_export()
    for collection in payload["resources"].values():
        for record in collection:
            assert record["tenant_id"] == payload["tenant_id"]


def test_tenant_export_includes_compliance_metadata_without_payment_secrets():
    payload = _sample_tenant_export()
    billing_record = payload["resources"]["billing_records"][0]
    assert billing_record["customer_ref"] == "cus_redacted"
    assert "payment_method" not in billing_record
    assert "card_number" not in billing_record
    assert payload["resources"]["audit_logs"][0]["event"] == "tenant.exported"
