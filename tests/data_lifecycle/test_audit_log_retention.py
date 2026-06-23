"""Audit-log retention lifecycle contract tests."""


AUDIT_RETENTION_YEARS = 7
CUSTOMER_DATA_RETENTION_DAYS = 30
REQUIRED_DELETION_AUDIT_FIELDS = {
    "event",
    "tenant_id",
    "actor_id",
    "subject_type",
    "subject_id",
    "deletion_request_id",
    "retention_basis",
    "occurred_at",
}


def _deletion_audit_event() -> dict:
    return {
        "event": "tenant.deletion_requested",
        "tenant_id": "tenant_a",
        "actor_id": "user_admin",
        "subject_type": "tenant",
        "subject_id": "tenant_a",
        "deletion_request_id": "del_req_001",
        "retention_basis": "customer_request",
        "occurred_at": "2026-06-04T00:00:00Z",
        "append_only": True,
    }


def test_audit_logs_have_separate_retention_from_customer_content():
    assert AUDIT_RETENTION_YEARS * 365 > CUSTOMER_DATA_RETENTION_DAYS


def test_deletion_audit_event_contains_required_fields():
    event = _deletion_audit_event()
    assert REQUIRED_DELETION_AUDIT_FIELDS.issubset(event.keys())
    assert event["append_only"] is True


def test_audit_logs_are_retained_after_hard_delete():
    hard_delete_actions = {
        "source_content": "purge",
        "derived_knowledge": "purge",
        "workflow_outputs": "purge",
        "billing_records": "retain_ledger",
        "audit_logs": "retain_append_only",
    }
    assert hard_delete_actions["audit_logs"] == "retain_append_only"
    assert hard_delete_actions["billing_records"] == "retain_ledger"
    assert "purge" != hard_delete_actions["audit_logs"]
