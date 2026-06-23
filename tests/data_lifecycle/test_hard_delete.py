"""Hard-delete lifecycle contract tests."""


PROTECTED_LEDGER_CATEGORIES = {"billing_records", "audit_logs"}
PURGEABLE_CATEGORIES = {"source_content", "derived_knowledge", "workflow_outputs", "workspace_metadata"}


def _hard_delete_plan(tenant_id: str) -> list[dict]:
    return [
        {"category": "source_content", "action": "purge", "tenant_id": tenant_id},
        {"category": "derived_knowledge", "action": "purge", "tenant_id": tenant_id},
        {"category": "workflow_outputs", "action": "purge", "tenant_id": tenant_id},
        {"category": "workspace_metadata", "action": "purge", "tenant_id": tenant_id},
        {"category": "user_identity", "action": "anonymize", "tenant_id": tenant_id},
        {"category": "tenant_profile", "action": "tombstone", "tenant_id": tenant_id},
        {"category": "billing_records", "action": "retain_ledger", "tenant_id": tenant_id},
        {"category": "audit_logs", "action": "retain_append_only", "tenant_id": tenant_id},
    ]


def test_hard_delete_purges_customer_controlled_content():
    plan = _hard_delete_plan("tenant_a")
    purge_categories = {step["category"] for step in plan if step["action"] == "purge"}
    assert purge_categories == PURGEABLE_CATEGORIES


def test_hard_delete_retains_billing_and_audit_ledgers():
    plan = _hard_delete_plan("tenant_a")
    protected = {step["category"]: step["action"] for step in plan if step["category"] in PROTECTED_LEDGER_CATEGORIES}
    assert protected == {"billing_records": "retain_ledger", "audit_logs": "retain_append_only"}


def test_hard_delete_plan_is_single_tenant_scoped():
    plan = _hard_delete_plan("tenant_a")
    assert {step["tenant_id"] for step in plan} == {"tenant_a"}
    assert all("tenant_b" not in step.values() for step in plan)
