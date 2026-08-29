# Global deny-by-default, tenant equality, agent-categorical, and
# known-action gating tests (design Section 11.1).

package fabric.authz.global_test

import data.fabric.authz

# ??? Fixtures ?????????????????????????????????????????????????????????????

active_human_view := {
    "schema_version": "fabric.authz.request.v1",
    "request_id": "req-view-1",
    "action": "claim.view",
    "principal": {"id": "p-1", "type": "human", "tenant_id": "t-1", "status": "active", "workflow_roles": ["workflow.economic_reviewer"]},
    "resource": {"type": "claim", "id": "c-1", "tenant_id": "t-1", "attributes": {}},
    "context": {"now": "2025-06-01T12:00:00Z"},
}

# ??? Allow: non-critical known action for an active same-tenant roleholder ?

test_non_critical_known_action_allowed if {
    authz.allow with input as active_human_view
}

# ??? Default deny ?????????????????????????????????????????????????????????

test_unknown_action_denied if {
    not authz.allow with input as _with_action(active_human_view, "claim.nonexistent")
    "UNKNOWN_ACTION" in authz.deny_reason with input as _with_action(active_human_view, "claim.nonexistent")
}

test_unknown_resource_type_denied if {
    not authz.allow with input as _with_resource(active_human_view, "gadget")
}

test_missing_workflow_role_denied if {
    not authz.allow with input as _strip_roles(active_human_view)
}

# ??? Agent categorical deny never granted by tenant equality or role ??????

test_agent_claim_approve_denied if {
    not authz.allow with input as _as_agent(active_human_view, "claim.approve")
    "AGENT_ACTION_FORBIDDEN" in authz.deny_reason with input as _as_agent(active_human_view, "claim.approve")
}

test_agent_deliverable_publish_denied if {
    not authz.allow with input as _as_agent(active_human_view, "deliverable.publish_external")
    "AGENT_ACTION_FORBIDDEN" in authz.deny_reason with input as _as_agent(active_human_view, "deliverable.publish_external")
}

# ??? Tenant equality is necessary, never sufficient ???????????????????????

test_tenant_mismatch_denied if {
    not authz.allow with input as _with_principal_tenant(active_human_view, "t-2")
    "TENANT_MISMATCH" in authz.deny_reason with input as _with_principal_tenant(active_human_view, "t-2")
}

# ??? Inactive principals fail closed ??????????????????????????????????????

test_inactive_principal_denied if {
    not authz.allow with input as _with_status(active_human_view, "inactive")
    "PRINCIPAL_INACTIVE" in authz.deny_reason with input as _with_status(active_human_view, "inactive")
}

# ??? Helpers ??????????????????????????????????????????????????????????????

_with_action(req, action) := {"principal": req.principal, "resource": req.resource, "context": req.context, "schema_version": req.schema_version, "request_id": req.request_id, "action": action}

_with_resource(req, rtype) := object.union(req, {"resource": object.union(req.resource, {"type": rtype})})

_with_principal_tenant(req, tenant) := object.union(req, {"principal": object.union(req.principal, {"tenant_id": tenant})})

_with_status(req, status) := object.union(req, {"principal": object.union(req.principal, {"status": status})})

_strip_roles(req) := object.union(req, {"principal": object.union(req.principal, {"workflow_roles": []})})

_as_agent(req, action) := object.union(req, {"action": action, "principal": object.union(req.principal, {"type": "agent"})})
