"""Central authorization policy registry for privileged actions.

This module is the single source of truth for action -> permission mapping
used by HTTP routes, agent tools, and internal execution paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import RequestContext, get_request_context
from .permissions import Permission, Role

try:
    from fastapi import HTTPException, status
except Exception:  # pragma: no cover - FastAPI is available in runtime/tests
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: Any = None) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _Status:
        HTTP_401_UNAUTHORIZED = 401
        HTTP_403_FORBIDDEN = 403

    status = _Status()


@dataclass(frozen=True)
class ActionPolicy:
    """Canonical policy for a privileged action."""

    required_permissions: tuple[str, ...]
    description: str


ACTION_POLICIES: dict[str, ActionPolicy] = {
    "layer4.tools.list": ActionPolicy((Permission.READ_AGENTS.value,), "List registered tools"),
    "layer4.tools.read_schema": ActionPolicy((Permission.READ_AGENTS.value,), "Read tool schema"),
    "layer4.tools.invoke": ActionPolicy((Permission.WRITE_AGENTS.value,), "Invoke an agent tool"),
    "layer4.tools.export_document": ActionPolicy((Permission.WRITE_AGENTS.value,), "Export business case artifacts"),
    "layer4.tools.read_export_audit": ActionPolicy((Permission.READ_AGENTS.value,), "Read export governance audit records"),
    "layer4.analysis.seed_auth_context": ActionPolicy((Permission.ADMIN_SYSTEM.value,), "Seed validation auth context"),
    "layer4.analysis.create_validation_session": ActionPolicy((Permission.ADMIN_SYSTEM.value,), "Create validation session"),
    "layer4.analysis.roi": ActionPolicy((Permission.WRITE_AGENTS.value,), "Run ROI analysis"),
    "layer4.analysis.whitespace": ActionPolicy((Permission.WRITE_AGENTS.value,), "Run whitespace analysis"),
    "layer4.analysis.generate_case": ActionPolicy((Permission.WRITE_AGENTS.value,), "Generate business case"),
    "layer4.analysis.regenerate_case": ActionPolicy((Permission.WRITE_AGENTS.value,), "Regenerate business case"),
    "layer4.analysis.read_case": ActionPolicy((Permission.READ_AGENTS.value,), "Read business case data"),
    "layer4.analysis.seed_case_lifecycle": ActionPolicy((Permission.ADMIN_SYSTEM.value,), "Seed business case lifecycle"),
    "layer4.analysis.export_case": ActionPolicy((Permission.READ_AGENTS.value,), "Export business case"),
    "layer4.analysis.list_cases": ActionPolicy((Permission.READ_AGENTS.value,), "List business cases"),
    "layer4.analysis.write_case": ActionPolicy((Permission.WRITE_AGENTS.value,), "Mutate business case workspace state"),
    "layer4.tool.admin.suspend_tenant": ActionPolicy((Permission.ADMIN_TENANTS.value,), "Suspend tenant"),
    "layer4.tool.knowledge.read_entity": ActionPolicy((Permission.READ_SEARCH.value,), "Read tenant-scoped knowledge entities"),
    "layer4.tool.knowledge.update_entity": ActionPolicy((Permission.WRITE_SCHEMA.value,), "Update tenant-scoped knowledge entities"),
    "layer4.tool.knowledge.delete_entity": ActionPolicy((Permission.WRITE_SCHEMA.value,), "Delete tenant-scoped knowledge entities"),
    "layer4.agent_tool.promote_signal": ActionPolicy((Permission.WRITE_AGENTS.value,), "Promote signal to hypothesis"),
    "layer4.agent_tool.validate_hypothesis": ActionPolicy((Permission.WRITE_AGENTS.value,), "Validate or reject hypothesis"),
    "layer5.truths.create": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create truth object"),
    "layer5.truths.list": ActionPolicy((Permission.READ_ANALYTICS.value,), "List truth objects"),
    "layer5.truths.sync_kg": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Sync approved truth objects to knowledge graph"),
    "layer5.truths.check_stale": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Trigger stale truth evaluation"),
    "layer5.truths.list_stale": ActionPolicy((Permission.READ_ANALYTICS.value,), "List stale truth objects"),
    "layer5.truths.freshness_summary": ActionPolicy((Permission.READ_ANALYTICS.value,), "Read freshness summary"),
    "layer5.truths.read": ActionPolicy((Permission.READ_ANALYTICS.value,), "Read truth object"),
    "layer5.truths.validate": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Validate truth object"),
    "layer5.truths.add_source": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Add truth evidence source"),
    "layer5.truths.read_audit": ActionPolicy((Permission.READ_ANALYTICS.value,), "Read truth audit trail"),
    "layer5.truths.delete": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Delete truth object"),
    "layer5.governance.formulas.create": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create governance formula"),
    "layer5.governance.formulas.list": ActionPolicy((Permission.READ_ANALYTICS.value,), "List governance formulas"),
    "layer5.governance.formulas.get": ActionPolicy((Permission.READ_ANALYTICS.value,), "Read governance formula"),
    "layer5.governance.formulas.create_version": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create governance formula version"),
    "layer5.governance.formulas.submit": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Submit governance formula for approval"),
    "layer5.governance.formulas.approve": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Approve governance formula"),
    "layer5.governance.formulas.reject": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Reject governance formula"),
    "layer5.governance.formulas.deprecate": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Deprecate governance formula"),
    "layer5.governance.formulas.archive": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Archive governance formula"),
    "layer5.governance.benchmarks.create": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create governance benchmark"),
    "layer5.governance.benchmarks.list": ActionPolicy((Permission.READ_ANALYTICS.value,), "List governance benchmarks"),
    "layer5.governance.benchmarks.create_version": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create governance benchmark version"),
    "layer5.governance.policies.create": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create governance policy"),
    "layer5.governance.policies.list": ActionPolicy((Permission.READ_ANALYTICS.value,), "List governance policies"),
    "layer5.governance.policies.evaluate": ActionPolicy((Permission.READ_ANALYTICS.value,), "Evaluate governance policy"),
    "layer5.governance.assumptions.create": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create governance assumption"),
    "layer5.governance.assumptions.list": ActionPolicy((Permission.READ_ANALYTICS.value,), "List governance assumptions"),
    "layer5.governance.assumptions.add_evidence": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Add governance assumption evidence"),
    "layer5.governance.assumptions.submit": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Submit governance assumption"),
    "layer5.governance.value_entries.create": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create value realization entry"),
    "layer5.governance.value_entries.list": ActionPolicy((Permission.READ_ANALYTICS.value,), "List value realization entries"),
    "layer5.governance.value_entries.update": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Update value realization entry"),
    "layer5.governance.approvals.list": ActionPolicy((Permission.READ_ANALYTICS.value,), "List governance approvals"),
    "layer5.governance.approvals.get": ActionPolicy((Permission.READ_ANALYTICS.value,), "Read governance approval"),
    "layer5.governance.approvals.approve": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Approve governance approval"),
    "layer5.governance.approvals.reject": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Reject governance approval"),
    "layer6.benchmarks.list": ActionPolicy((Permission.READ_ANALYTICS.value,), "List benchmark datasets"),
    "layer6.benchmarks.read": ActionPolicy((Permission.READ_ANALYTICS.value,), "Read benchmark dataset"),
    "layer6.benchmarks.write": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Create or update benchmark dataset"),
    "layer6.benchmarks.compare": ActionPolicy((Permission.READ_ANALYTICS.value,), "Run benchmark comparison"),
    "layer6.benchmarks.validate": ActionPolicy((Permission.READ_ANALYTICS.value,), "Validate value against benchmark"),
    "layer6.benchmarks.industries": ActionPolicy((Permission.READ_ANALYTICS.value,), "List benchmark industries"),
    "layer5.academy.read": ActionPolicy((Permission.READ_ANALYTICS.value,), "Read academy content"),
    "layer5.academy.write": ActionPolicy((Permission.WRITE_ANALYTICS.value,), "Write academy progress and assessments"),
}


TOOL_ACTIONS: dict[str, str] = {
    "export_document": "layer4.tools.export_document",
    "get_entity": "layer4.tool.knowledge.read_entity",
    "search_entities": "layer4.tool.knowledge.read_entity",
    "list_entities": "layer4.tool.knowledge.read_entity",
    "update_entity": "layer4.tool.knowledge.update_entity",
    "delete_entity": "layer4.tool.knowledge.delete_entity",
    "promote_signal": "layer4.agent_tool.promote_signal",
    "validate_hypothesis": "layer4.agent_tool.validate_hypothesis",
    "suspend_tenant": "layer4.tool.admin.suspend_tenant",
}


def get_action_policy(action: str) -> ActionPolicy | None:
    """Return the registered policy for *action*."""
    return ACTION_POLICIES.get(action)


def get_tool_action(tool_name: str) -> str | None:
    """Return the canonical action key for *tool_name* when one is registered."""
    return TOOL_ACTIONS.get(tool_name)


def list_action_policies() -> dict[str, ActionPolicy]:
    """Return a shallow copy of the policy registry for inventory/testing."""
    return dict(ACTION_POLICIES)


def _permission_values(context: RequestContext) -> set[str]:
    values = {
        permission.value if isinstance(permission, Permission) else str(permission)
        for permission in (context.permissions or frozenset())
    }
    values.update(str(scope) for scope in (context.service_account_scopes or []))
    return values


def _build_auth_required_detail(action: str) -> dict[str, Any]:
    return {
        "code": "AUTHENTICATION_REQUIRED",
        "message": f"Authenticated context is required for action '{action}'",
        "action": action,
    }


def _build_forbidden_detail(
    action: str,
    required_permissions: tuple[str, ...],
    *,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "action": action,
        "required_permissions": list(required_permissions),
    }


def authorize_action(
    action: str,
    context: RequestContext | None = None,
    *,
    target_tenant_id: str | None = None,
) -> RequestContext:
    """Authorize *action* for the current or supplied request context.

    Raises ``HTTPException`` with a stable 401/403 body on failure.
    """

    ctx = context or get_request_context()
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_build_auth_required_detail(action),
        )

    policy = get_action_policy(action)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_build_forbidden_detail(
                action,
                tuple(),
                code="AUTHORIZATION_POLICY_MISSING",
                message=f"No authorization policy is registered for action '{action}'",
            ),
        )

    if ctx.has_any_role(Role.SUPER_ADMIN, Role.SYSTEM):
        return ctx

    permission_values = _permission_values(ctx)
    missing_permissions = [
        permission for permission in policy.required_permissions if permission not in permission_values
    ]
    if missing_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_build_forbidden_detail(
                action,
                policy.required_permissions,
                code="INSUFFICIENT_SCOPE",
                message=f"Insufficient scope for action '{action}'",
            ),
        )

    if target_tenant_id is not None and str(ctx.tenant_id) != str(target_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_build_forbidden_detail(
                action,
                policy.required_permissions,
                code="TENANT_SCOPE_MISMATCH",
                message=f"Tenant scope does not permit action '{action}' on the requested resource",
            ),
        )

    return ctx


__all__ = [
    "ActionPolicy",
    "ACTION_POLICIES",
    "TOOL_ACTIONS",
    "authorize_action",
    "get_action_policy",
    "get_tool_action",
    "list_action_policies",
]
