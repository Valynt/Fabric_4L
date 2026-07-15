"""Retention policy documentation and invariant tests."""

from pathlib import Path

README = Path(__file__).with_name("README.md")

EXPECTED_RETENTION_RULES = {
    "source_content": "30 days",
    "system_telemetry": "30 days",
    "derived_knowledge": "90 days",
    "workflow_outputs": "90 days",
    "billing_records": "7 years",
    "audit_logs": "7 years",
}

EXPECTED_DOCUMENTED_CATEGORIES = {
    "tenant_profile",
    "workspace_metadata",
    "account_profile",
    "user_identity",
    "source_content",
    "derived_knowledge",
    "workflow_outputs",
    "billing_records",
    "audit_logs",
    "system_telemetry",
    "backups_archives",
}


def _readme_text() -> str:
    return README.read_text(encoding="utf-8")


def test_data_categories_are_documented():
    text = _readme_text()
    for category in EXPECTED_DOCUMENTED_CATEGORIES:
        assert f"| {category} |" in text


def test_retention_policy_is_documented_by_category():
    text = _readme_text()
    for category, retention in EXPECTED_RETENTION_RULES.items():
        row = next(line for line in text.splitlines() if line.startswith(f"| {category} |"))
        assert retention in row


def test_lifecycle_export_schema_version_is_documented():
    text = _readme_text()
    assert "data-lifecycle-export.v1" in text
    for required_field in (
        "schema_version",
        "export_id",
        "export_scope",
        "tenant_id",
        "subject",
        "generated_at",
        "requested_by",
        "data_categories",
        "resources",
        "redactions",
        "audit_chain",
        "checksums",
    ):
        assert f'"{required_field}"' in text


def test_user_tenant_and_workspace_deletion_behavior_is_documented():
    text = _readme_text()
    assert "User, tenant, and workspace deletion follows a two-phase lifecycle" in text
    assert "Soft delete records the deletion request" in text
    assert "Hard delete purges customer-controlled content and PII" in text
    assert "Billing records and audit logs are retained under their own retention rules" in text
