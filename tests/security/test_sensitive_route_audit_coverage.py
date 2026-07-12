"""Coverage tests for structured audit logging on sensitive Layer 4 routes."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SENSITIVE_ROUTE_AUDIT_EXPECTATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "services/layer4-agents/src/layer4_agents/tenants/api/routes/api_keys.py",
        ("@router.post", "@router.delete", "emit_audit_event", "AuditAction.API_KEY_"),
    ),
    (
        "services/layer4-agents/src/layer4_agents/tenants/api/routes/oidc.py",
        ('@router.get("/callback"', "emit_audit_event", "AuditAction.OIDC_LOGIN"),
    ),
    (
        "services/layer4-agents/src/layer4_agents/tenants/api/routes/provisioning.py",
        ("@router.post", "emit_audit_event", "AuditAction.TENANT_PROVISIONED_WEBHOOK"),
    ),
    (
        "services/layer4-agents/src/layer4_agents/api/routes/crm_webhooks.py",
        ("@router.post", "emit_audit_event", "AuditAction.WEBHOOK_PROCESSING_FAILED"),
    ),
    (
        "services/layer4-agents/src/layer4_agents/api/routes/integrations.py",
        ("@router.post", "@router.delete", "emit_audit_event", "AuditAction."),
    ),
)


def test_sensitive_routes_reference_structured_audit_primitives() -> None:
    missing: list[str] = []

    for relative_path, required_snippets in SENSITIVE_ROUTE_AUDIT_EXPECTATIONS:
        module_text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        absent = [snippet for snippet in required_snippets if snippet not in module_text]
        if absent:
            missing.append(f"{relative_path}: missing {absent}")

    assert not missing, "\n".join(missing)
